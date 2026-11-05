from django.urls import path

from .views import (
    signup, ProfileEditView, PasswordChangeCustomView,
    user_management_view, edit_user_groups, group_management_view,
    edit_group_permissions, toggle_staff, richiesta_accesso_pratica,
    profile_view, profile_settore_check, profile_incomplete_users,
    commissioni_list, commissione_edit, commissione_delete,
    commissione_iscritti, mie_commissioni, CustomLoginView,
)
from . import views


app_name = 'accounts'

urlpatterns = [
    # Login custom (redirige i consiglieri a 'Le mie Commissioni')
    path('login/', CustomLoginView.as_view(), name='login'),
    path('signup/', signup, name='signup'),
    path('profile/', profile_view, name='profile_view_url'),
    path('profile/settore-check/', views.profile_settore_check, name='profile_settore_check_url'),
    path('profile/edit/', ProfileEditView.as_view(), name='profile_edit'),
    path('password-change/', PasswordChangeCustomView.as_view(), name='password_change'),
    path('mie-commissioni/', mie_commissioni, name='mie_commissioni_url'),

     # Gestione Utenti, Gruppi e Permessi
    path('management/users/', views.user_management_view, name='user_management_url'),
    path('management/users/<int:user_id>/groups/', views.edit_user_groups, name='edit_user_groups_url'),
    path('management/users/<int:user_id>/staff/', views.toggle_staff, name='toggle_staff_url'),
    path('management/groups/', views.group_management_view, name='group_management_url'),
    path('management/groups/<int:group_id>/permissions/', views.edit_group_permissions, name='edit_group_permissions_url'),

    # Gestione Commissioni
    path('management/commissioni/', commissioni_list, name='commissioni_list_url'),
    path('management/commissioni/new/', commissione_edit, name='commissione_new_url'),
    path('management/commissioni/<int:pk>/edit/', commissione_edit, name='commissione_edit_url'),
    path('management/commissioni/<int:pk>/delete/', commissione_delete, name='commissione_delete_url'),
    path('management/commissioni/<int:pk>/iscritti/', commissione_iscritti, name='commissione_iscritti_url'),

     path('richiesta-accesso/<int:pk>/', richiesta_accesso_pratica, name='richiesta_accesso'),
    path('richiesta-accesso/edilizia/<int:pk>/', richiesta_accesso_pratica, {'tipo': 'edilizia'}, name='richiesta_accesso_edilizia'),

    path('ajax/struttura-choices/', views.struttura_choices_api, name='struttura_choices_api'),

    # Verifica profili incompleti (admin)
    path('management/profile-incomplete/', views.profile_incomplete_users, name='profile_incomplete_users_url'),
]
