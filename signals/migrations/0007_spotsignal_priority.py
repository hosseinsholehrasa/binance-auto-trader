# Generated by Django 3.1.7 on 2021-08-03 14:10

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('signals', '0006_spotcontroler_cancel_orders'),
    ]

    operations = [
        migrations.AddField(
            model_name='spotsignal',
            name='priority',
            field=models.IntegerField(blank=True, null=True),
        ),
    ]