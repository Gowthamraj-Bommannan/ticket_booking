from django.contrib import admin
from .models import Train, TrainClass

class TrainClassInline(admin.TabularInline):
    model = TrainClass
    extra = 1

@admin.register(Train)
class TrainAdmin(admin.ModelAdmin):
    list_display = ('train_number', 'name', 'train_type', 'running_days_display', 'created_at')
    search_fields = ('train_number', 'name')
    list_filter = ('train_type', 'created_at')
    inlines = [TrainClassInline]
    readonly_fields = ('train_number', 'created_at', 'updated_at')
    
    def running_days_display(self, obj):
        return ', '.join(obj.running_days) if obj.running_days else '-'
    running_days_display.short_description = 'Running Days'
    
    def get_readonly_fields(self, request, obj=None):
        if obj:  # Editing an existing object
            return self.readonly_fields
        else:  # Creating a new object
            return ('created_at', 'updated_at')

@admin.register(TrainClass)
class TrainClassAdmin(admin.ModelAdmin):
    list_display = ('train', 'class_type', 'seat_capacity')
    list_filter = ('class_type', 'train')
    search_fields = ('train__name', 'train__train_number')
