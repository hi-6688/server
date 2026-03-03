import sys
from bs4 import BeautifulSoup
import copy

def update_html():
    with open('/home/terraria/servers/web_interface/admin.html', 'r', encoding='utf-8') as f:
        admin_soup = BeautifulSoup(f.read(), 'html.parser')

    with open('/home/terraria/servers/web_interface/frontend/dist/index.html', 'r', encoding='utf-8') as f:
        new_soup = BeautifulSoup(f.read(), 'html.parser')
        
    # 1. Add FontAwesome and admin.css and admin.js to head of new_soup
    head = new_soup.find('head')
    
    fa_link = new_soup.new_tag('link', rel='stylesheet', href='https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css')
    css_link = new_soup.new_tag('link', rel='stylesheet', href='admin.css?v=10')
    js_script = new_soup.new_tag('script', src='admin.js?v=30', defer=True)
    
    head.append(fa_link)
    head.append(css_link)
    head.append(js_script)
    
    # 2. Add modals and overlays to the body of new_soup
    body = new_soup.find('body')
    modals = ['loginModal', 'instanceModal', 'editorModal', 'loadingOverlay']
    for m in modals:
        el = admin_soup.find(id=m)
        if el:
            el_copy = copy.copy(el)
            body.insert(0, el_copy)
            
    file_input = admin_soup.find('input', id='fileInput')
    if file_input:
        body.insert(0, copy.copy(file_input))
        
    # 3. Migrate sections to main-content
    main_content = new_soup.find('main', id='main-content')
    if main_content:
        # clear existing dummy portfolio content
        main_content.clear()
        
        # Add server instances dropdown or panel AT THE TOP of main_content
        # Let's create a glass-panel for the instance list
        instance_panel = new_soup.new_tag('div')
        instance_panel['class'] = 'glass-panel p-4 mb-4'
        instance_panel['style'] = 'display: flex; gap: 10px; align-items: center; overflow-x: auto;'
        
        title = new_soup.new_tag('div')
        title['style'] = 'font-weight: bold; margin-right: 15px;'
        title.string = '伺服器列表 (Instances)'
        instance_panel.append(title)
        
        btn = new_soup.new_tag('button', onclick='openInstanceModal()')
        btn['class'] = 'px-3 py-1 rounded bg-green-500 text-white'
        btn.string = '+'
        instance_panel.append(btn)
        
        inst_list = admin_soup.find(id='instanceList')
        if inst_list:
            inst_list_copy = copy.copy(inst_list)
            inst_list_copy['style'] = 'display: flex; gap: 10px; flex: 1;'
            instance_panel.append(inst_list_copy)
            
        main_content.append(instance_panel)
        
        # Now copy all .section
        sections = admin_soup.find_all('div', class_='section')
        for sec in sections:
            sec_copy = copy.copy(sec)
            
            # replace .card with .glass-panel to maintain the theme
            for card in sec_copy.find_all('div', class_='card'):
                classes = card.get('class', [])
                if 'card' in classes:
                    classes.remove('card')
                classes.append('glass-panel')
                classes.append('p-4')
                card['class'] = classes
                card['style'] = card.get('style', '') + '; background: rgba(17, 24, 39, 0.7); backdrop-filter: blur(16px);'
                
            main_content.append(sec_copy)
            
    # 4. Update the navigation links in the new Navbar
    nav_links_container = new_soup.find('nav').find('div', class_='hidden md:flex')
    if nav_links_container:
        links = nav_links_container.find_all('a')
        
        targets = ['dashboard', 'options', 'worlds', 'gamerules', 'players']
        for i, link in enumerate(links):
            if i < len(targets):
                link['onclick'] = f"showSection('{targets[i]}')"
                # If they are currently active or not. The UI template handles hover, we can just let it be.
                link['href'] = '#'
                
                # Make text white and add hover
                if 'nav-item' not in link.get('class', []):
                    link['class'] = link.get('class', []) + ['nav-item']
                
    # 5. Fix admin.css overriding our body layout.
    with open('/home/terraria/servers/web_interface/admin.css', 'r', encoding='utf-8') as f:
        admin_css = f.read()
    
    # Strip body {} html {} * {}
    import re
    admin_css = re.sub(r'body\s*\{[^}]*\}', '', admin_css)
    admin_css = re.sub(r'\*\s*\{[^}]*\}', '', admin_css)
    admin_css = re.sub(r'html\s*\{[^}]*\}', '', admin_css)
    
    with open('/home/terraria/servers/web_interface/admin.css', 'w', encoding='utf-8') as f:
        f.write(admin_css)

    # 6. Save new index.html
    with open('/home/terraria/servers/web_interface/frontend/dist/index.html', 'w', encoding='utf-8') as f:
        f.write(str(new_soup))

if __name__ == '__main__':
    update_html()
    print("Success: Ported UI from admin.html to index.html")
