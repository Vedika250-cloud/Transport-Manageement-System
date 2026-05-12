import os, glob, re

path = 'c:/Users/vedik/OneDrive/Desktop/TMS 18/TMS/TMS/templates/'
files = glob.glob(path + 'add_*.html') + glob.glob(path + 'edit_*.html')

form_container_re = re.compile(r'class=\"form-container\"[^>]*style=\"[^\"]*\"')
input_style_re = re.compile(r'\s*style=\"width:100%;[^\"]*\"')

for f in files:
    with open(f, 'r', encoding='utf-8') as file:
        content = file.read()
    
    # Remove inline style on form-container
    content = form_container_re.sub('class="form-container"', content)
    
    # Remove inline style on inputs
    content = input_style_re.sub('', content)
    
    # Fix h2 header inside form-container
    content = content.replace('<h2 style="margin-bottom: 20px;">', '<div class="form-header"><h2>')
    content = content.replace('<h2 style="margin-bottom: 30px; text-align: center;">', '<div class="form-header"><h2>')
    content = content.replace('</h2>', '</h2></div>')
    
    with open(f, 'w', encoding='utf-8') as file:
        file.write(content)
print('Forms cleaned.')
