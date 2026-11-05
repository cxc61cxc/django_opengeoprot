from django.db.models.signals import post_save
from django.contrib.auth.models import User
from django.dispatch import receiver
from .models import Profile


@receiver(post_save, sender=User)
def create_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)


# NB: non registriamo piu' un receiver save_profile perche' l'istanza
# Profile in-memory risulta "stale" dopo che il form aggiorna i campi
# via Profile.objects.update_or_create (ad es. in SignUpForm.save):
# il successivo user.save() scatenato da login/update_last_login
# richiama instance.profile.save() e ripristina settore=None/u_o=''
# nel database.