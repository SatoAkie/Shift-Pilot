# Generated by Django 5.2.3 on 2025-06-30 18:05

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('shifts', '0008_remove_usershift_shift_pattern_and_more'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='usershift',
            name='created_at',
        ),
        migrations.RemoveField(
            model_name='usershift',
            name='updated_at',
        ),
        migrations.AddField(
            model_name='usershift',
            name='is_manual',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='usershift',
            name='shift_pattern',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='shifts.shiftpattern'),
        ),
        migrations.AlterField(
            model_name='usershift',
            name='shift',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='shifts.shift'),
        ),
    ]
