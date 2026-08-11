from django.db import models
from django.contrib.auth.models import AbstractUser

# Create your models here.

class Majmuat(models.Model):
    MAJMUAT_CHOICES = [
        ('Susee', 'Majmuat Suseey'),
        ('Nafiul Madneey', 'Majmuat Nafiul Madneey'),
        ('Hafs', 'Majmuat Hafs '),
    ]
    name = models.CharField(max_length=100, choices=MAJMUAT_CHOICES, unique=True)
    
    def __str__(self):
        return self.name

class Teacher(models.Model):
    # Each teacher teaches ONE class (all 3 subjects to that class)
    name = models.CharField(max_length=100)
    assigned_class = models.OneToOneField(
        Majmuat,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='teacher+'
    )
    
    def __str__(self):
        return f"{self.username} - {self.assigned_class.name if self.assigned_class else 'No Class Assigned'}"

# class Student(AbstractUser):
#     # Each student belongs to ONE class
#     student_class = models.ForeignKey(
#         Majmuat, 
#         on_delete=models.CASCADE,
#         # related_name='students'
#     )
    
#     def __str__(self):
#         return f"{self.username} - {self.student_class.name}"

# class Course(models.Model):
#     SUBJECT_CHOICES = [
#         ('Tahfeez', 'Mathematics'),
#         ('Tajweed', 'Science'),
#         ('Huruf', 'Huruf'),
#     ]
    
#     name = models.CharField(max_length=20, choices=SUBJECT_CHOICES)
    
#     def __str__(self):
#         return f"{self.name}"

# class Attendance(models.Model):
#     student = models.ForeignKey(Student, on_delete=models.CASCADE)
#     course = models.ForeignKey(Course, on_delete=models.CASCADE)
#     date = models.DateField(auto_now_add=True)
#     is_present = models.BooleanField(default=False)
    
#     class Meta:
#         # Prevent duplicate attendance records for the same student, course, and date
#         unique_together = ['student', 'course', 'date']  
    
#     def __str__(self):
#         return f"{self.student.username} - {self.course.name} - {self.date} - {'Present' if self.is_present else 'Absent'}"
