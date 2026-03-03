import sys
from bs4 import BeautifulSoup
import copy

def update_html():
    with open('/home/terraria/servers/web_interface/admin_old.html', 'r', encoding='utf-8') as f:
        admin_soup = BeautifulSoup(f.read(), 'html.parser')

    with open('/home/terraria/servers/web_interface/frontend/dist/index.html', 'r', encoding='utf-8') as f:
        new_soup = BeautifulSoup(f.read(), 'html.parser')
        
    head = new_soup.find('head')
    
    # Check avoiding duplicates
    if 'font-awesome' not in str(head):
        fa_link = new_soup.new_tag('link', rel='stylesheet', href='https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css')
        head.append(fa_link)
    
    if 'admin.css' not in str(head):
        css_link = new_soup.new_tag('link', rel='stylesheet', href='admin.css?v=11')
        head.append(css_link)
        
    if 'admin.js' not in str(head):
        js_script = new_soup.new_tag('script', src='admin.js?v=31', defer=True)
        head.append(js_script)
    
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
        
    # Migrate sections to main
    main_content = new_soup.find('main')
    if main_content:
        # clear existing dummy portfolio content
        main_content.clear()
        
        # Add server instances dropdown or panel AT THE TOP of main_content
        instance_panel = new_soup.new_tag('div')
        instance_panel['class'] = 'glass-panel p-6 mb-4 flex items-center gap-4 rounded-3xl'
        
        title = new_soup.new_tag('div')
        title['class'] = 'font-bold text-white uppercase tracking-widest'
        title.string = '伺服器列表 (Instances)'
        instance_panel.append(title)
        
        btn = new_soup.new_tag('button', onclick='openInstanceModal()')
        btn['class'] = 'px-4 py-2 rounded-xl bg-green-500/20 text-green-400 hover:bg-green-500/40 transition-colors'
        btn.string = '+ 新增 (New)'
        instance_panel.append(btn)
        
        inst_list = admin_soup.find(id='instanceList')
        if inst_list:
            inst_list_copy = copy.copy(inst_list)
            del inst_list_copy['style']  # remove max-height
            inst_list_copy['class'] = 'flex gap-4 overflow-x-auto custom-scrollbar flex-1'
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
                classes.extend(['glass-panel', 'p-6', 'rounded-2xl', 'text-white/90'])
                card['class'] = classes
                if card.has_attr('style'):
                    # remove conflicting background styles
                    style = card['style']
                    style = style.replace('background:var(--bg-panel);', '')
                    card['style'] = style
                
            main_content.append(sec_copy)
            
    # Update the navigation links in the new Navbar
    nav = new_soup.find('nav')
    if nav:
        nav_links_container = nav.find('div', class_='hidden md:flex')
        if nav_links_container:
            links = nav_links_container.find_all('a')
            targets = ['dashboard', 'options', 'worlds', 'gamerules', 'players']
            for i, link in enumerate(links):
                if i < len(targets):
                    link['onclick'] = f"showSection('{targets[i]}')"
                    link['href'] = '#'
                    classes = link.get('class', [])
                    if 'nav-item' not in classes:
                        classes.append('nav-item')
                    # Make it look clickable
                    classes.append('cursor-pointer')
                    link['class'] = classes
                
    with open('/home/terraria/servers/web_interface/admin.html', 'w', encoding='utf-8') as f:
        f.write(str(new_soup))

if __name__ == '__main__':
    update_html()
    print("Success: Ported UI from admin_old.html to admin.html correctly")
