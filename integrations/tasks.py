from celery import shared_task
from django.utils import timezone


@shared_task
def sync_google_contacts_task(config_id):
    """Background task to sync Google contacts."""
    from integrations.models import GoogleWorkspaceConfig
    from integrations.services import MockGoogleContactsService
    
    try:
        config = GoogleWorkspaceConfig.objects.get(pk=config_id, is_active=True)
        if config.sync_enabled:
            MockGoogleContactsService.fetch_contacts(config)
            return f"Synced contacts for {config.name}"
        return "Sync disabled"
    except GoogleWorkspaceConfig.DoesNotExist:
        return "Config not found"
    except Exception as e:
        return f"Error: {str(e)}"


@shared_task
def sync_shopify_orders_task(store_id):
    """Background task to sync Shopify orders."""
    from integrations.models import ShopifyStore
    from integrations.services import MockShopifyService
    
    try:
        store = ShopifyStore.objects.get(pk=store_id, is_active=True)
        if store.sync_enabled:
            MockShopifyService.sync_orders(store)
            return f"Synced orders for {store.name}"
        return "Sync disabled"
    except ShopifyStore.DoesNotExist:
        return "Store not found"
    except Exception as e:
        return f"Error: {str(e)}"


@shared_task
def sync_all_google_contacts():
    """Sync contacts for all enabled Google configs."""
    from integrations.models import GoogleWorkspaceConfig
    
    configs = GoogleWorkspaceConfig.objects.filter(is_active=True, sync_enabled=True)
    results = []
    
    for config in configs:
        result = sync_google_contacts_task.delay(str(config.id))
        results.append(str(config.id))
    
    return f"Queued sync for {len(results)} configs"


@shared_task
def sync_all_shopify_stores():
    """Sync orders for all enabled Shopify stores."""
    from integrations.models import ShopifyStore
    
    stores = ShopifyStore.objects.filter(is_active=True, sync_enabled=True)
    results = []
    
    for store in stores:
        result = sync_shopify_orders_task.delay(str(store.id))
        results.append(str(store.id))
    
    return f"Queued sync for {len(results)} stores"
