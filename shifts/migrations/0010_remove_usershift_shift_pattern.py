# Generated by Django 5.2.3 on 2025-07-02 14:37

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('shifts', '0009_remove_usershift_created_at_and_more'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='usershift',
            name='shift_pattern',
        ),
    ]
