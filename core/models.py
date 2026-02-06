from django.db import models

# Create your models here.

class Actor(models.Model):
    name = models.CharField(max_length=100)
    nationality = models.CharField(max_length=50)
    birth_date = models.DateField()
    gender = models.CharField(max_length=10)

    def __str__(self):
        return self.name

