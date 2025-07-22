from django.contrib import admin
from .models import Train, TrainClass, TrainSchedule

admin.site.register(Train)
admin.site.register(TrainClass)
admin.site.register(TrainSchedule)