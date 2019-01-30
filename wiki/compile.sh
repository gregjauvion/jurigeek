
### the main wiki page
pandoc source/main-page.md -s -H source/style.css -o build/main-page.html

### strategy
pandoc source/data.md -s -H source/style.css -o build/data.html
pandoc source/model.md -s -H source/style.css -o build/model.html
pandoc source/todo.md -s -H source/style.css -o build/todo.html
