from django import forms

class EmailForm(forms.Form):
    # recipient = forms.EmailField(label='Indirizzo Email',
    #                              help_text='Inserisci un\'indirizzo mail valido!',
    #                              widget=forms.TextInput)
    message = forms.CharField(label='messaggio',
                              
                              widget=forms.Textarea(attrs={'autofocus': True}))
