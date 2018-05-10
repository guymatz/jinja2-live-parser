# -*- coding: utf-8 -*-
from flask import Flask, render_template, request, escape
from jinja2 import Template, Environment, meta
from random import choice
import json
import yaml
# For dynamic loading of filters
import imp
from inspect import getmembers, isfunction
import os
import sys
from sshclient import SshClient

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
      app.logger.warning("Adding %s" % os.path.join(e[0], f))
      filter_files.append(os.path.join(e[0], f))

for jfilter in filter_files:
    mod_name, file_ext = os.path.splitext(os.path.split(jfilter)[-1])
    try:
        py_mod = imp.load_source(mod_name, jfilter)
    except Exception as e:
        app.logger.warning("Couldn't import %s: %s" % (jfilter, e))
        next
    for name, function in getmembers(py_mod):
            if isfunction(function) and not name.startswith('_'):
                # Saving filter info to put it in HTML at some point
                added_filters[name] = function.__doc__
                # add filter to jinja
                app.jinja_env.filters[name] = function
    try:
        filter_module = imp.load_source('%s.FilterModule' % mod_name, jfilter)
        filters = filter_module.FilterModule().filters()
        for fname, func in filters.iteritems():
            if not added_filters.get(fname, None):
                try:
                    # app.logger.warning("Adding %s from FilterModule of %s" % (fname, mod_name))
                    # Saving filter info to put it in HTML at some point
                    added_filters[fname] = func.__doc__
                    # add filter to jinja
                    app.jinja_env.filters[fname] = func
                except Exception as e:
                    app.logger.warning("Couldn't import %s from %s.FilterModule: %s" % (fname, mod_name, e))
            else:
                app.logger.warning("Function %s already exists.  New doc: %s" % (fname, func.__doc__))
    except Exception as e:
        app.logger.warning("Couldn't import FilterModule from %s: %s" % (mod_name, e))


# These are the added filters.  must add these name + doc strings to the html
# Also do this for built-in jinja filters
#for f in sorted(added_filters):
#    app.logger.warning("%s: %s" % (f, added_filters[f]))

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

#    for field in request.form.keys():
#        app.logger.debug("%s: %s\n" % (field, request.form[field]))

    if int(request.form['dummyvalues']):
        # List variables (introspection)
        env = Environment()
        vars_to_fill = meta.find_undeclared_variables(env.parse(request.form['template']))

        for v in vars_to_fill:
            values[v] = choice(dummy_values)
    else:
        #import pdb; pdb.set_trace()
        if int(request.form['use_yaml']):
            if yaml.load(request.form['values']):
                values = yaml.load(request.form['values'])
        else:
            if json.loads(request.form['values']):
                values = json.loads(request.form['values'])

        app.logger.warning("Values (%s): %s" % (type(values), str(values)))
        remote_server = request.form['remote_server']
        remote_username = request.form['remote_username']
        remote_password = request.form['remote_password']
        app.logger.warning("Remote Server: %s" % remote_server)
        if int(request.form['use_remote_data']) and remote_server != '':
            try:
                values['pillar'] = grab_data(remote_server, remote_username, remote_password, 'pillar')
                app.logger.warning("Pillar: %s" % values['pillar'])
                values['grains'] = grab_data(remote_server, remote_username, remote_password, 'grains')
                app.logger.warning("Grains: %s" % values['grains'])
            except ValueError as e:
                values['ERROR'] = "Value Error: %s" % e
                app.logger.warning(values['ERROR'])
            except Exception as e:
                values['ERROR'] = "Regular Error: %s" % str(e)
                app.logger.warning(values['ERROR'])

            if values.get('ERROR'):
                app.logger.warning(values['ERROR'])
                return escape(values['ERROR'])

    app.logger.warning(str(values))
    app.logger.warning(yaml.dump(values), sys.stdout)
    try:
        rendered_tpl = tpl.render(values)
    except Exception as e:
        app.logger.warning("Ooops: %s" % e)
        return str(e)

    if int(request.form['showwhitespaces']):
        # Replace whitespaces with a visible character (will be grayed with javascript)
        rendered_tpl = rendered_tpl.replace(' ', u'•')

    return rendered_tpl.replace('\n', '<br />')


def grab_data(remote_host, username, password, salt_data):
    client = SshClient(host=remote_host, username=username, password=password)
    cmd = 'salt-call --out=yaml %s.items' % salt_data
    ret = None
    out, errors, retval = None, None, None
    try:
        ret = client.execute(cmd, sudo=True)
        errors = "".join(ret['err'])
        out = "".join(ret["out"])
        retval = ret["retval"]
        #import pdb; pdb.set_trace()
    except Exception as e:
        raise Exception(str(ret))
    finally:
        client.close()
    if len(errors) > 0:
        raise ValueError('salt-call error: %s' % errors)
    else:
        yaml_out = yaml.load(out)
        return yaml_out['local']


if __name__ == "__main__":
    app.debug = True
    app.run(host= '0.0.0.0')
