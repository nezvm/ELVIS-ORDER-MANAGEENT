"""
Shopify Webhook Views

Handles incoming webhooks from Shopify for:
- orders/create
- orders/update  
- checkouts/update (abandoned checkouts)
- fulfillments/create
- fulfillments/update
"""
import json
import logging
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.http import HttpResponse, JsonResponse

from integrations.models import ShopifyStore
from .services import (
    ShopifyWebhookService,
    ShopifyOrderService, 
    ShopifyCheckoutService,
    ShopifyFulfillmentService
)

logger = logging.getLogger(__name__)


@csrf_exempt
@require_http_methods(["POST"])
def shopify_webhook(request):
    """
    Universal Shopify webhook endpoint.
    Routes based on X-Shopify-Topic header.
    
    Endpoint: /webhooks/shopify/
    """
    topic = request.headers.get('X-Shopify-Topic', '')
    shop_domain = request.headers.get('X-Shopify-Shop-Domain', '')
    
    logger.info(f"Shopify webhook received: {topic} from {shop_domain}")
    
    # Get store
    store = ShopifyWebhookService.get_store_from_request(request)
    
    # Verify webhook if store has secret
    if store and store.webhook_secret:
        if not ShopifyWebhookService.verify_webhook(request, store.webhook_secret):
            logger.warning(f"Webhook verification failed for {shop_domain}")
            return HttpResponse("Unauthorized", status=401)
    
    # Parse payload
    try:
        payload = json.loads(request.body)
    except json.JSONDecodeError:
        return HttpResponse("Invalid JSON", status=400)
    
    # Log webhook
    log = ShopifyWebhookService.log_webhook(store, topic, payload, request)
    
    if not store:
        log.error_message = f"Store not found for domain: {shop_domain}"
        log.save()
        # Still return 200 to prevent Shopify from retrying
        return HttpResponse("Store not found", status=200)
    
    # Route to appropriate handler
    try:
        if topic.startswith('orders/'):
            ShopifyOrderService.process_order_webhook(store, payload, log)
        elif topic.startswith('checkouts/'):
            ShopifyCheckoutService.process_checkout_webhook(store, payload, log)
        elif topic.startswith('fulfillments/'):
            ShopifyFulfillmentService.process_fulfillment_webhook(store, payload, log)
        else:
            log.action_taken = 'unhandled_topic'
            log.save()
            logger.info(f"Unhandled webhook topic: {topic}")
        
        return HttpResponse("OK", status=200)
        
    except Exception as e:
        logger.error(f"Webhook processing error: {e}")
        return HttpResponse("Processing error", status=200)  # Still 200 to prevent retries


@csrf_exempt
@require_http_methods(["POST"])
def shopify_orders_webhook(request):
    """
    Shopify orders webhook endpoint.
    
    Endpoint: /webhooks/shopify/orders/
    
    Handles: orders/create, orders/update, orders/cancelled
    """
    topic = request.headers.get('X-Shopify-Topic', 'orders/create')
    store = ShopifyWebhookService.get_store_from_request(request)
    
    if store and store.webhook_secret:
        if not ShopifyWebhookService.verify_webhook(request, store.webhook_secret):
            return HttpResponse("Unauthorized", status=401)
    
    try:
        payload = json.loads(request.body)
    except json.JSONDecodeError:
        return HttpResponse("Invalid JSON", status=400)
    
    log = ShopifyWebhookService.log_webhook(store, topic, payload, request)
    
    if not store:
        log.error_message = "Store not found"
        log.save()
        return HttpResponse("OK", status=200)
    
    try:
        ShopifyOrderService.process_order_webhook(store, payload, log)
        return HttpResponse("OK", status=200)
    except Exception as e:
        logger.error(f"Order webhook error: {e}")
        return HttpResponse("OK", status=200)


@csrf_exempt
@require_http_methods(["POST"])
def shopify_checkouts_webhook(request):
    """
    Shopify checkouts webhook endpoint for abandoned checkouts.
    
    Endpoint: /webhooks/shopify/checkouts/
    
    Handles: checkouts/create, checkouts/update
    """
    topic = request.headers.get('X-Shopify-Topic', 'checkouts/update')
    store = ShopifyWebhookService.get_store_from_request(request)
    
    if store and store.webhook_secret:
        if not ShopifyWebhookService.verify_webhook(request, store.webhook_secret):
            return HttpResponse("Unauthorized", status=401)
    
    try:
        payload = json.loads(request.body)
    except json.JSONDecodeError:
        return HttpResponse("Invalid JSON", status=400)
    
    log = ShopifyWebhookService.log_webhook(store, topic, payload, request)
    
    if not store:
        log.error_message = "Store not found"
        log.save()
        return HttpResponse("OK", status=200)
    
    try:
        ShopifyCheckoutService.process_checkout_webhook(store, payload, log)
        return HttpResponse("OK", status=200)
    except Exception as e:
        logger.error(f"Checkout webhook error: {e}")
        return HttpResponse("OK", status=200)


@csrf_exempt
@require_http_methods(["POST"])
def shopify_fulfillments_webhook(request):
    """
    Shopify fulfillments webhook endpoint.
    
    Endpoint: /webhooks/shopify/fulfillments/
    
    Handles: fulfillments/create, fulfillments/update
    """
    topic = request.headers.get('X-Shopify-Topic', 'fulfillments/create')
    store = ShopifyWebhookService.get_store_from_request(request)
    
    if store and store.webhook_secret:
        if not ShopifyWebhookService.verify_webhook(request, store.webhook_secret):
            return HttpResponse("Unauthorized", status=401)
    
    try:
        payload = json.loads(request.body)
    except json.JSONDecodeError:
        return HttpResponse("Invalid JSON", status=400)
    
    log = ShopifyWebhookService.log_webhook(store, topic, payload, request)
    
    if not store:
        log.error_message = "Store not found"
        log.save()
        return HttpResponse("OK", status=200)
    
    try:
        ShopifyFulfillmentService.process_fulfillment_webhook(store, payload, log)
        return HttpResponse("OK", status=200)
    except Exception as e:
        logger.error(f"Fulfillment webhook error: {e}")
        return HttpResponse("OK", status=200)
