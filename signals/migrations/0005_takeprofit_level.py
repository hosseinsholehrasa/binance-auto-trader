# Generated by Django 3.1.4 on 2021-08-02 14:18

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('signals', '0004_auto_20210802_1815'),
    ]

    operations = [
        migrations.AddField(
            model_name='takeprofit',
            name='level',
            field=models.IntegerField(default=1),
        ),
    ]
