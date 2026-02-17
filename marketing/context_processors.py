"""
Centralized Marketing sidebar menu definition.

Single source of truth for the Marketing navigation.
Items are sorted by the ``order`` field at render time.

Each entry
----------
order : int
    Determines display position (ascending).
label : str
    Display text in the sidebar.
url_name : str
    Django URL name (namespaced with ``marketing:``).
url_suffix : str, optional
    Query-string to append (e.g. ``?lead_source=whatsapp``).
icon : str
    Font Awesome class string.
icon_color : str
    Tailwind text-color utility.
test_id : str
    ``data-testid`` for E2E tests.
active_paths : list[str]
    Substrings of ``request.path`` (or ``request.get_full_path()``)
    that mark this item as active.
badge : str | None
    Optional small badge text (e.g. "New").
badge_color : str
    Tailwind class for badge background.
indent : bool
    If True, item gets extra left-padding (sub-item look).
"""


MARKETING_MENU = [
    {
        "order": 10,
        "label": "ROAS Dashboard",
        "url_name": "marketing:meta_overview",
        "icon": "fas fa-chart-line",
        "icon_color": "text-blue-400",
        "test_id": "nav-marketing-overview",
        "active_paths": ["/marketing/overview"],
        "badge": "New",
        "badge_color": "bg-blue-600",
    },
    {
        "order": 20,
        "label": "All Leads",
        "url_name": "marketing:lead_list",
        "icon": "fas fa-user-plus",
        "icon_color": "",
        "test_id": "nav-leads",
        "active_paths": ["/marketing/lead-list", "/marketing/leads"],
    },
    {
        "order": 30,
        "label": "WhatsApp Leads",
        "url_name": "marketing:lead_list",
        "url_suffix": "?lead_source=whatsapp",
        "icon": "fab fa-whatsapp",
        "icon_color": "text-green-400",
        "test_id": "nav-whatsapp-leads",
        "active_match_full_path": "lead_source=whatsapp",
        "indent": True,
    },
    {
        "order": 40,
        "label": "Shopify Leads",
        "url_name": "marketing:leads_shopify",
        "icon": "fab fa-shopify",
        "icon_color": "text-purple-400",
        "test_id": "nav-shopify-leads",
        "active_paths": ["/marketing/leads/shopify"],
        "indent": True,
    },
    {
        "order": 50,
        "label": "Campaign Performance",
        "url_name": "marketing:meta_campaigns",
        "icon": "fab fa-meta",
        "icon_color": "text-blue-500",
        "test_id": "nav-meta-campaigns",
        "active_paths": ["/marketing/meta/campaigns"],
    },
    {
        "order": 60,
        "label": "CAPI Event Logs",
        "url_name": "marketing:capi_logs",
        "icon": "fas fa-database",
        "icon_color": "text-purple-400",
        "test_id": "nav-capi-logs",
        "active_paths": ["/marketing/meta/capi"],
    },
    {
        "order": 70,
        "label": "Meta Settings",
        "url_name": "marketing:meta_settings",
        "icon": "fab fa-facebook",
        "icon_color": "text-blue-600",
        "test_id": "nav-meta-settings",
        "active_paths": ["/marketing/meta/settings"],
    },
    {
        "order": 80,
        "label": "WhatsApp Broadcast",
        "url_name": "marketing:whatsapp_dashboard",
        "icon": "fab fa-whatsapp",
        "icon_color": "",
        "test_id": "nav-whatsapp",
        "active_paths": ["/marketing/whatsapp"],
    },
    {
        "order": 90,
        "label": "Campaigns",
        "url_name": "marketing:campaign_list",
        "icon": "fas fa-bullhorn",
        "icon_color": "",
        "test_id": "nav-campaigns",
        "active_paths": ["/marketing/campaign"],
    },
    {
        "order": 100,
        "label": "Market Insights",
        "url_name": "marketing:insights",
        "icon": "fas fa-chart-pie",
        "icon_color": "",
        "test_id": "nav-insights",
        "active_paths": ["/marketing/insights"],
    },
]


def marketing_menu(request):
    """Template context processor that returns the ordered marketing menu."""
    from django.urls import reverse, NoReverseMatch

    items = []
    for item in sorted(MARKETING_MENU, key=lambda x: x["order"]):
        # Resolve URL
        try:
            url = reverse(item["url_name"])
        except NoReverseMatch:
            url = "#"
        url += item.get("url_suffix", "")

        # Determine active state
        is_active = False
        full_path = request.get_full_path()
        path = request.path

        # Special full-path match (e.g. query-string matching)
        if item.get("active_match_full_path"):
            if item["active_match_full_path"] in full_path:
                is_active = True
        else:
            for ap in item.get("active_paths", []):
                if ap in path:
                    is_active = True
                    break

        items.append({
            "order": item["order"],
            "label": item["label"],
            "url": url,
            "icon": item["icon"],
            "icon_color": item.get("icon_color", ""),
            "test_id": item.get("test_id", ""),
            "badge": item.get("badge"),
            "badge_color": item.get("badge_color", "bg-blue-600"),
            "indent": item.get("indent", False),
            "is_active": is_active,
        })

    return {"marketing_menu": items}
