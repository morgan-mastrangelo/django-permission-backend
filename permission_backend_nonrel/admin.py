from django import forms
from django.conf import settings
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.admin.sites import NotRegistered
from django.contrib.auth.models import User, Group, Permission

from .models import UserPermissionList, GroupPermissionList
from .utils import update_permissions_user, \
     update_user_groups, update_permissions_group, get_permission_choices


class UserForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ('username', 'email', 'first_name', 'last_name', 'is_active',
                  'is_staff', 'is_superuser')


class NonrelPermissionUserForm(UserForm):
    user_permissions = forms.MultipleChoiceField(required=False)
    groups = forms.MultipleChoiceField(required=False)
    
    def __init__(self, *args, **kwargs):
        super(NonrelPermissionUserForm, self).__init__(*args, **kwargs)

        self.fields['user_permissions'] = forms.MultipleChoiceField(required=False)
        self.fields['groups'] = forms.MultipleChoiceField(required=False)
        
        self.fields['user_permissions'].choices = get_permission_choices()
        
        group_objs = Group.objects.all()
        choices = []
        for group_obj in group_objs:
            choices.append([group_obj.id, group_obj.name])
        self.fields['groups'].choices = choices

        try:
            user_perm_list = UserPermissionList.objects.get(
                user=kwargs['instance'])
            self.fields['user_permissions'].initial = user_perm_list.permission_fk_list
            self.fields['groups'].initial = user_perm_list.group_fk_list
        except (UserPermissionList.DoesNotExist, KeyError):
            self.fields['user_permissions'].initial = list()
            self.fields['groups'].initial = list()          
      

class NonrelPermissionCustomUserAdmin(UserAdmin):
    fieldsets = None
    form = NonrelPermissionUserForm
    
    def save_model(self, request, obj, form, change):
        super(NonrelPermissionCustomUserAdmin, self).save_model(request, obj, form, change)
        try:
            if len(form.cleaned_data['user_permissions']) > 0:
                permissions = list(Permission.objects.filter(
                    id__in=form.cleaned_data['user_permissions']).order_by('name'))
            else:
                permissions = []

            update_permissions_user(permissions, obj)
        except KeyError:
            pass
        
        try:
            if len(form.cleaned_data['groups']) > 0:
                groups = list(Group.objects.filter(
                    id__in=form.cleaned_data['groups']))
            else:
                groups = []

            update_user_groups(obj, groups)
        except KeyError:
            pass


class PermissionAdmin(admin.ModelAdmin):
    ordering = ('name',)


class GroupForm(forms.ModelForm):
    permissions = forms.MultipleChoiceField(required=False)
    
    def __init__(self, *args, **kwargs):
        super(GroupForm, self).__init__(*args, **kwargs)

        self.fields['permissions'] = forms.MultipleChoiceField(required=False)
   
        self.fields['permissions'].choices = get_permission_choices()

        try:
            current_perm_list = GroupPermissionList.objects.get(
                group=kwargs['instance'])
            self.fields['permissions'].initial = current_perm_list.permission_fk_list
        except (GroupPermissionList.DoesNotExist, KeyError):
            self.fields['permissions'].initial = []
        
    class Meta:
        model = Group
        fields = ('name',)


class CustomGroupAdmin(admin.ModelAdmin):
    form = GroupForm
    fieldsets = None

    def save_model(self, request, obj, form, change):
        super(CustomGroupAdmin, self).save_model(request, obj, form, change)

        if len(form.cleaned_data['permissions']) > 0:
            permissions = list(Permission.objects.filter(
                id__in=form.cleaned_data['permissions']).order_by('name'))
        else:
            permissions = []
            

        update_permissions_group(permissions, obj)

try:
    admin.site.unregister(User)
except NotRegistered:
    pass

try:
    admin.site.unregister(Group)
except NotRegistered:
    pass

admin.site.register(User, NonrelPermissionCustomUserAdmin)
admin.site.register(Permission, PermissionAdmin)
admin.site.register(Group, CustomGroupAdmin)
