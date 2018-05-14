# -*- coding: utf-8 -*-
from flask import Flask, render_template, request, escape
from jinja2 import Template, Environment, meta
import logging
from random import choice
import json
import yaml
# For dynamic loading of filters
import imp
import ast
import inspect
import os
import sys
from sshclient import SshClient

app = Flask(__name__)

#sys.path.append('../ansible/lib/ansible')

# Load filters in filters dir
filter_path='filters'
filter_files = []
added_filters = {}


def find_decorated(target, decorator_method):
    res = {}
    def visit_function_def(node):
        res[node.name] = [ast.dump(e) for e in node.decorator_list]
    V = ast.NodeVisitor()
    V.visit_FunctionDef = visit_function_def
    V.visit(compile(inspect.getsource(target), '?', 'exec', ast.PyCF_ONLY_AST))
    # returning methods that are decorated, e.g.
    # base64_b64encode ["Call(func=Name(id='jinja_filter', ctx=Load()), args=[Str(s='base64_encode')], keywords=[])"]
    return [ f for f in res.keys() if len(res[f]) > 0 and decorator_method in res[f][0] ]


# Find py files and turn then into filterpath/blah/filter.py
for e in os.walk(filter_path, followlinks=True):
    for f in e[2]:
        if f.endswith('py'):
            if 'yaml' in f:
                print("Skipping * %s" % f)
                next
            app.logger.debug("Adding debug %s" % os.path.join(e[0], f))
            app.logger.info("Adding info %s" % os.path.join(e[0], f))
            app.logger.warning("Adding warning %s" % os.path.join(e[0], f))
            app.logger.error("Adding error %s" % os.path.join(e[0], f))
            print("Checking for filters  %s" % os.path.join(e[0], f))
            filter_files.append(os.path.join(e[0], f))
print("All filters  %s" % sorted(filter_files))

for jfilter in filter_files:
    if 'yaml' in jfilter:
        print("Skipping * %s" % name)
        next
    mod_name, file_ext = os.path.splitext(os.path.split(jfilter)[-1])
    py_mod = None
    try:
        py_mod = imp.load_source(mod_name, jfilter)
    except Exception as e:
        app.logger.debug("Couldn't import %s: %s" % (jfilter, e))
        print("Couldn't import %s: %s" % (jfilter, e))
        next
    py_mod_decorated = find_decorated(py_mod, 'jinja_filter')
    for name, func in inspect.getmembers(py_mod):
        if 'yaml' in name:
            print("Skipping ** %s" % name)
            next
        if inspect.isfunction(func) and not name.startswith('_') and name in py_mod_decorated:
            # Saving filter info to put it in HTML at some point
            added_filters[name] = func.__doc__
            # add filter to jinja
            app.jinja_env.filters[name] = func
            print("Added filter %s from %s" % (name, jfilter))
    try:
        filter_module = imp.load_source('%s.FilterModule' % mod_name, jfilter)
        filters = filter_module.FilterModule().filters()
        for fname, ffunc in filters.iteritems():
            if 'yaml' in fname:
                print("Skipping *** %s" % name)
                next
            if not added_filters.get(fname, None):
                try:
                    # app.logger.warning("Adding %s from FilterModule of %s" % (fname, mod_name))
                    # Saving filter info to put it in HTML at some point
                    added_filters[fname] = ffunc.__doc__
                    # add filter to jinja
                    app.jinja_env.filters[fname] = ffunc
                except Exception as e:
                    app.logger.warning("Couldn't import %s from %s.FilterModule: %s" % (fname, mod_name, e))
            else:
                app.logger.warning("Function %s already exists.  New doc: %s" % (fname, ffunc.__doc__))
    except Exception as e:
        app.logger.warning("Couldn't import FilterModule from %s: %s" % (mod_name, e))


#import pdb; pdb.set_trace()
# These are the added filters.  must add these name + doc strings to the html
# Also do this for built-in jinja filters
for f in sorted(added_filters):
    app.logger.warning("%s: %s" % (f, added_filters[f]))
    doc_string = str(added_filters.get(f, 'No Description'))
    doc_string = doc_string.split('\n')[0]
    print("%s: %s" % (f, doc_string))


@app.route("/")
def hello():
    return render_template('index.html', all_filters=app.jinja_env.filters)


@app.route('/convert', methods=['GET', 'POST'])
def convert():
    dummy_values = [ 'Lorem', 'Ipsum', 'Amet', 'Elit', 'Expositum', 
        'Dissimile', 'Superiori', 'Laboro', 'Torquate', 'sunt', 
    ]

    tpl = app.jinja_env.from_string(request.form['template'])
    values = {}
    pillar_values = None

#    for field in request.form.keys():
#        app.logger.debug("%s: %s\n" % (field, request.form[field]))

    if int(request.form['dummyvalues']):
        # List variables (introspection)
        env = Environment()
        vars_to_fill = meta.find_undeclared_variables(env.parse(request.form['template']))

        for v in vars_to_fill:
            values[v] = choice(dummy_values)
    else:
        try:
            values_str = request.form['values']
            if int(request.form['use_json']):
                pillar_values = json.loads(values_str)
            else:
                app.logger.warning("About to try to parse yaml: %s" % dir())
                #import pdb; pdb.set_trace()
                pillar_values = yaml.load(values_str)
        except Exception as e:
            app.logger.warning("Could not parse additional data: %s" % e)

        app.logger.warning("Values: %s" % pillar_values)
        remote_server = request.form['remote_server']
        remote_username = request.form['remote_username']
        remote_password = request.form['remote_password']
        app.logger.warning("Remote Server: %s" % remote_server)
        if int(request.form['use_remote_data']) and remote_server != '':
            try:
                import pdb; pdb.set_trace()
                values['pillar'] = grab_data(remote_server, remote_username, remote_password, 'pillar')
                app.logger.warning("Pillar: %s" % values['pillar'])
                values['grains'] = grab_data(remote_server, remote_username, remote_password, 'grains')
                app.logger.warning("Grains: %s" % values['grains'])
            except ValueError as e:
                values['ERROR'] = "Value Error: %s" % e
                app.logger.warning(values['ERROR'])
            except Exception as e:
                print("Error: %s" % e)
                values['ERROR'] = "Regular Error: %s" % e
                app.logger.warning(values['ERROR'])

            if values.get('ERROR'):
                app.logger.warning(values['ERROR'])
                return escape(values['ERROR'])

    # Add the user-supplied Pillar Data to pillar data
    for k, v in pillar_values.items():
        values['pillar'][k] = v
    app.logger.warning(str(values))
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
    except Exception as e:
        raise Exception(str(ret))
    finally:
        client.close()
    if len(errors) > 0:
        raise ValueError('salt-call error: %s' % errors)
    else:
        import yaml
        yaml_out = yaml.load(out)
        return yaml_out['local']



if __name__ == "__main__":
    app.debug = True
    app.run(host= '0.0.0.0')
