from django.db import models

# Create your models here.
class Project(models.Model):
    title = models.CharField(max_length=200, default='Sin título')
    description = models.TextField(default='Sin descripción')
    technology = models.CharField(max_length=200, default='Desconocida')
    created_at = models.DateTimeField(auto_now_add=True)  # No necesita default si es auto_now_add
    
    def __str__(self):
        return self.title

class Task(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField()
    project = models.ForeignKey(Project, on_delete=models.CASCADE)
    done = models.BooleanField(default=False)
    
    def __str__(self):
        return self.title + ' -> (' + self.project.name + ')'