import sys
from bs4 import BeautifulSoup

def update_html():
    with open('/home/terraria/servers/web_interface/frontend/dist/index.html', 'r', encoding='utf-8') as f:
        html_content = f.read()

    soup = BeautifulSoup(html_content, 'html.parser')
    
    # 1. Ensure material symbols is in head
    head = soup.find('head')
    if head and 'Material+Symbols+Outlined' not in str(head):
        new_link = soup.new_tag('link')
        new_link['href'] = "https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:opsz,wght,FILL,GRAD@20..48,100..700,0..1,-50..200"
        new_link['rel'] = "stylesheet"
        head.append(new_link)

    # 2. Fix the body padding
    body = soup.find('body')
    if body:
        # Add pt-24 or similar top padding to account for fixed navbar
        classes = body.get('class', [])
        if 'pt-24' not in classes:
            classes.append('pt-24')
        if 'lg:pt-28' not in classes:
            classes.append('lg:pt-28')
        body['class'] = classes

    # 3. Modify nav to be fixed
    nav = soup.find('nav')
    if nav:
        classes = nav.get('class', [])
        # Remove previous width/margin/rounded if we make it fully fixed at top
        classes_to_remove = ['rounded-3xl', 'mb-4', 'p-4']
        classes = [c for c in classes if c not in classes_to_remove]
        
        # Add fixed positioning
        classes_to_add = ['fixed', 'top-0', 'left-0', 'right-0', 'w-full', 'px-6', 'py-4', 'shadow-lg', 'backdrop-blur-md', 'bg-black/40', 'border-b', 'border-white/10']
        for c in classes_to_add:
            if c not in classes:
                classes.append(c)
        nav['class'] = classes

    # 4. Remove display: none from #main-content if it's there
    main_content = soup.find('main', id='main-content')
    if main_content:
        style = main_content.get('style', '')
        if 'display: none' in style:
            main_content['style'] = style.replace('display: none;', '').replace('display:none;', '')
            
    # Also if there's a welcome-screen, hide it by default so we can see the main layout
    welcome_screen = soup.find('div', id='welcome-screen')
    if welcome_screen:
        style = welcome_screen.get('style', '')
        if 'display: none' not in style:
            welcome_screen['style'] = style + '; display: none;'

    # 5. Fix the background
    # Background is defined in CSS data-purpose="custom-glassmorphism", let's leave it as is if it's there.
    
    with open('/home/terraria/servers/web_interface/frontend/dist/index.html', 'w', encoding='utf-8') as f:
        f.write(str(soup))

if __name__ == '__main__':
    update_html()
    print("Success: Refactored HTML layout fixed navbar.")
