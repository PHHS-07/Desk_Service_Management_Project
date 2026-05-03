from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0006_activitylog_managerprofile_requestattachment'),
    ]

    operations = [
        migrations.AddField(
            model_name='managerprofile',
            name='role',
            field=models.CharField(blank=True, choices=[('developer', 'Developer'), ('project_manager', 'Project Manager'), ('tester', 'Tester')], max_length=30),
        ),
    ]
