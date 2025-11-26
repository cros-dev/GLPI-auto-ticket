from django.db import migrations, models


def populate_full_path(apps, schema_editor):
    GlpiCategory = apps.get_model('core', 'GlpiCategory')

    for category in GlpiCategory.objects.all():
        path = []
        current = category
        while current:
            path.insert(0, current.name)
            current = current.parent
        category.full_path = ' > '.join(path)
        category.save(update_fields=['full_path'])


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0006_remove_ticket_glpi_type'),
    ]

    operations = [
        migrations.AddField(
            model_name='glpicategory',
            name='full_path',
            field=models.CharField(blank=True, default='', help_text="Caminho completo (ex.: 'TI > Requisição > Acesso')", max_length=1024),
        ),
        migrations.RunPython(populate_full_path, migrations.RunPython.noop),
    ]

