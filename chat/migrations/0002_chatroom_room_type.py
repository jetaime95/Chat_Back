# Generated by Django 5.1.4 on 2025-01-18 16:44

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('chat', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='chatroom',
            name='room_type',
            field=models.CharField(choices=[('direct', 'Direct Message'), ('group', 'Group Chat')], default='direct', max_length=10),
        ),
    ]
