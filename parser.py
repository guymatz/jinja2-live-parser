# -*- coding: utf-8 -*-
from flask import Flask, render_template, request
from jinja2 import Template, Environment, meta
from random import choice
import json
import yaml
# For dynamic loading of filters
import imp
from inspect import getmembers, isfunction
import os, sys

app = Flask(__name__)

sys.path.append('../ansible/lib/ansible')

# Load filters in filters dir
filter_path='filters'
filter_files =  [ ]
added_filters = {}

# Find py files and turn then into filterpath/blah/filter.py
for e in os.walk(filter_path, followlinks=True):
  for f in e[2]:
    if f.endswith('py'):
      print("Adding %s" % os.path.join(e[0], f))
      filter_files.append(os.path.join(e[0], f))

for filter in filter_files:
    mod_name,file_ext = os.path.splitext(os.path.split(filter)[-1])
    try:
        py_mod = imp.load_source(mod_name, filter)
    except Exception as e:
        print("COuldn't import %s: %s" % (filter, e))
        next
    for name, function in getmembers(py_mod):
            if isfunction(function) and not name.startswith('_'):
                # Saving filter info to put it in HTML at some point
                added_filters[name] = function.__doc__
                # add filter to jinja
                app.jinja_env.filters[name] = function
    try:
        filter_module = imp.load_source('%s.FilterModule' % mod_name, filter)
        filters = filter_module.FilterModule().filters()
        for fname, func in filters.iteritems():
            if not added_filters.get(fname, None):
                try:
                    # print("Adding %s from FilterModule of %s" % (fname, mod_name))
                    # Saving filter info to put it in HTML at some point
                    added_filters[fname] = func.__doc__
                    # add filter to jinja
                    app.jinja_env.filters[fname] = func
                except Exception as e:
                    print("Couldn't import %s from %s.FilterModule: %s" % (fname, mod_name, e))
            else:
                print("Function %s already exists.  New doc: %s" % (fname, func.__doc__))
    except Exception as e:
        print("Couldn't import FilterModule from %s: %s" % (mod_name, e))


# These are the added filters.  must add these name + doc strings to the html
# Also do this for built-in jinja filters
#for f in sorted(added_filters):
#    print("%s: %s" % (f, added_filters[f]))

@app.route("/")
def hello():
    return render_template('index.html',
                      all_filters = app.jinja_env.filters
           )


@app.route('/convert', methods=['GET', 'POST'])
def convert():
    dummy_values = [ 'Lorem', 'Ipsum', 'Amet', 'Elit', 'Expositum', 
        'Dissimile', 'Superiori', 'Laboro', 'Torquate', 'sunt', 
    ]

    tpl = app.jinja_env.from_string(request.form['template'])
    values = {}

    if int(request.form['dummyvalues']):
        # List variables (introspection)
        env = Environment()
        vars_to_fill = meta.find_undeclared_variables(env.parse(request.form['template']))

        for v in vars_to_fill:
            values[v] = choice(dummy_values)
    else:
        if int(request.form['use_yaml']):
            values = yaml.load(request.form['values'])
        else:
            values = json.loads(request.form['values'])

    rendered_tpl = tpl.render(values)

    if int(request.form['showwhitespaces']):
        # Replace whitespaces with a visible character (will be grayed with javascript)
        rendered_tpl = rendered_tpl.replace(' ', u'•')

    return rendered_tpl.replace('\n', '<br />')

if __name__ == "__main__":
    app.debug = True
    app.run(host= '0.0.0.0')
