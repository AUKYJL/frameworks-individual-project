from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("planner", "0001_initial")]

    operations = [
        migrations.AddField(
            model_name="task", name="status",
            field=models.CharField(
                max_length=9, default="ACTIVE",
                choices=[("ACTIVE", "В работе"), ("COMPLETED", "Выполнено"),
                         ("CANCELLED", "Отменено")],
            ),
        ),
        migrations.AddField(
            model_name="category", name="slug",
            field=models.SlugField(max_length=120, null=True, blank=True),
        ),
    ]
