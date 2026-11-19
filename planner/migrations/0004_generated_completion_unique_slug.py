from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("planner", "0003_transfer_statuses_and_slugs")]

    operations = [
        migrations.RemoveField(model_name="task", name="is_completed"),
        migrations.AddField(
            model_name="task", name="is_completed",
            field=models.GeneratedField(
                expression=models.Case(
                    models.When(status="COMPLETED", then=models.Value(True)),
                    default=models.Value(False),
                    output_field=models.BooleanField(),
                ),
                output_field=models.BooleanField(), db_persist=True,
            ),
        ),
        migrations.AlterField(
            model_name="category", name="slug",
            field=models.SlugField(max_length=120, unique=True, blank=True),
        ),
    ]
