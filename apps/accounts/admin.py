from django.contrib import admin

from apps.administrations.models import RegistrationRequest
from apps.administrations.services import process_registration_approval, process_registration_rejection


@admin.register(RegistrationRequest)
class RegistrationRequestAdmin(admin.ModelAdmin):
    list_display = ('fio', 'group', 'email', 'created_at', 'status')
    list_filter = ('status',)
    search_fields = ('fio', 'email', 'group')
    list_editable = ('status',)
    readonly_fields = ('fio', 'group', 'phone', 'email', 'created_at')

    def save_model(self, request, obj, form, change):
        if change:
            old_obj = RegistrationRequest.objects.get(pk=obj.pk)
            if old_obj.status != obj.status:
                if obj.status == "approved":
                    process_registration_approval(obj)
                elif obj.status == "rejected":
                    process_registration_rejection(obj)
        super().save_model(request, obj, form, change)
