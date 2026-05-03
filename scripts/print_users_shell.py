from django.contrib.auth.models import User
import pprint
managers = list(User.objects.filter(is_staff=True, is_superuser=False).order_by('-date_joined').values('id','username','email','date_joined')[:20])
clients = list(User.objects.filter(is_staff=False, is_superuser=False).order_by('-date_joined').values('id','username','email','date_joined')[:20])

pprint.pprint({'managers': managers, 'clients': clients})
