# Generated by Django 5.2.3 on 2025-07-03 12:09

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('shifts', '0011_shift_is_rest'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='shift',
            name='is_rest',
        ),
        migrations.AddField(
            model_name='shiftpattern',
            name='is_rest',
            field=models.BooleanField(default=False),
        ),
    ]
