import calendar
import re
from datetime import date, datetime

from django import template
from django.conf import settings


register = template.Library()


@register.filter(name="times")
def times(number):
    return range(number)


@register.filter()
def class_name(value):
    return value.__class__.__name__


@register.filter()
def make_title(value):
    return re.sub(r"(\w)([A-Z])", r"\1 \2", value)


def pop_and_get_app(apps, key, app_label):
    for index, app in enumerate(apps):
        if app[key] == app_label:
            return apps.pop(index)
    return None


@register.filter
def sort_apps(apps):
    new_apps = []
    order = settings.APP_ORDER
    for app_label in order.keys():
        obj = pop_and_get_app(apps, "app_label", app_label)
        if obj:
            new_apps.append(obj)
    apps = new_apps + apps
    for app in apps:
        models = app.get("models")
        app_label = app.get("app_label")
        new_models = []
        order_models = settings.APP_ORDER.get(app_label, [])
        for model in order_models:
            obj = pop_and_get_app(models, "object_name", model)
            if obj:
                new_models.append(obj)
        models = new_models + models
        app["models"] = models
    return apps


@register.filter
def month_name(month_number):
    return calendar.month_name[month_number]


@register.filter
def user_type_allowed(user_type, allowed_types):
    return user_type in allowed_types


@register.filter
def filter_by_status(objects, status):
    return objects.filter(status=status)


@register.filter
def get_item(dictionary, key):
    return dictionary.get(key)


@register.filter
def timezone_offset(time_obj, offset):
    time_dt = datetime.combine(date.today(), time_obj)
    result_dt = time_dt - offset
    return result_dt
