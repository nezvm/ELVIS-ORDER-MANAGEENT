"""
Wabis WhatsApp BSP - Celery Tasks

Background tasks for automatic subscriber sync and lead management.
"""

import logging
from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task(bind=True, name='integrations.wabis.sync_wabis_subscribers')
def sync_wabis_subscribers(self):
    """
    Sync all subscribers from Wabis API to local database.
    Runs automatically every 15 minutes via Celery Beat.
    """
    from integrations.wabis.models import WabisConfig, WabisNumber, WabisSyncLog
    from integrations.wabis.api_client import WabisAPIClient, WabisSubscriberSyncService
    
    logger.info("Starting automatic Wabis subscriber sync...")
    
    # Get active config
    config = WabisConfig.objects.filter(is_active=True).first()
    if not config or not config.api_key:
        logger.warning("Wabis sync skipped: No API token configured")
        return {'status': 'skipped', 'reason': 'No API token configured'}
    
    # Get all numbers with configured bot IDs
    numbers_with_bot_id = WabisNumber.objects.filter(
        is_active=True,
        wabis_bot_id__isnull=False
    ).exclude(wabis_bot_id='')
    
    if not numbers_with_bot_id.exists():
        logger.warning("Wabis sync skipped: No numbers with Bot ID configured")
        return {'status': 'skipped', 'reason': 'No numbers with Bot ID configured'}
    
    # Initialize API client and sync service
    client = WabisAPIClient(api_token=config.api_key)
    sync_service = WabisSubscriberSyncService(client)
    
    total_stats = {
        'numbers_synced': 0,
        'total_created': 0,
        'total_updated': 0,
        'total_errors': 0,
        'total_processed': 0,
    }
    
    # Sync each number
    for number in numbers_with_bot_id:
        try:
            logger.info(f"Syncing subscribers for {number.display_name} (Bot ID: {number.wabis_bot_id})")
            
            stats = sync_service.sync_all_subscribers(
                whatsapp_bot_id=number.wabis_bot_id,
                wabis_number=number,
                config=config
            )
            
            total_stats['numbers_synced'] += 1
            total_stats['total_created'] += stats.get('created', 0)
            total_stats['total_updated'] += stats.get('updated', 0)
            total_stats['total_errors'] += stats.get('errors', 0)
            total_stats['total_processed'] += stats.get('total', 0)
            
            logger.info(f"Synced {number.display_name}: {stats}")
            
        except Exception as e:
            logger.error(f"Error syncing {number.display_name}: {e}")
            total_stats['total_errors'] += 1
            
            # Log the error
            WabisSyncLog.objects.create(
                sync_type='subscribers',
                status='failed',
                error_message=f"Error syncing {number.display_name}: {str(e)}"
            )
    
    # Update last sync time on config
    config.last_sync_at = timezone.now()
    config.save(update_fields=['last_sync_at', 'updated'])
    
    logger.info(f"Wabis sync completed: {total_stats}")
    
    return {
        'status': 'completed',
        **total_stats
    }


@shared_task(bind=True, name='integrations.wabis.expire_pending_leads')
def expire_pending_leads(self):
    """
    Mark leads as Lost if they haven't converted within the matching period (7 days).
    Runs daily at 02:00 IST.
    """
    from integrations.wabis.services import WabisConversionService
    
    logger.info("Starting Wabis pending lead expiration...")
    
    try:
        count = WabisConversionService.expire_pending_leads()
        logger.info(f"Expired {count} pending leads to Lost status")
        return {'status': 'completed', 'expired_count': count}
    except Exception as e:
        logger.error(f"Error expiring leads: {e}")
        return {'status': 'error', 'error': str(e)}


@shared_task(bind=True, name='integrations.wabis.sync_single_number')
def sync_single_number(self, number_id):
    """
    Sync subscribers for a single WhatsApp number.
    Can be triggered manually or scheduled.
    """
    from integrations.wabis.models import WabisConfig, WabisNumber, WabisSyncLog
    from integrations.wabis.api_client import WabisAPIClient, WabisSubscriberSyncService
    
    logger.info(f"Starting sync for number ID: {number_id}")
    
    try:
        number = WabisNumber.objects.get(id=number_id, is_active=True)
    except WabisNumber.DoesNotExist:
        return {'status': 'error', 'error': 'Number not found'}
    
    if not number.wabis_bot_id:
        return {'status': 'skipped', 'reason': 'No Bot ID configured'}
    
    config = WabisConfig.objects.filter(is_active=True).first()
    if not config or not config.api_key:
        return {'status': 'error', 'error': 'No API token configured'}
    
    client = WabisAPIClient(api_token=config.api_key)
    sync_service = WabisSubscriberSyncService(client)
    
    try:
        stats = sync_service.sync_all_subscribers(
            whatsapp_bot_id=number.wabis_bot_id,
            wabis_number=number,
            config=config
        )
        
        logger.info(f"Synced {number.display_name}: {stats}")
        return {'status': 'completed', **stats}
        
    except Exception as e:
        logger.error(f"Error syncing {number.display_name}: {e}")
        return {'status': 'error', 'error': str(e)}
