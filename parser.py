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
#sys.path.append('filters/salt')

# Load filters in filters dir
jinja_filter_path='filters'

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
                #import ipdb; ipdb.set_trace()
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
                #import ipdb; ipdb.set_trace()
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
        yaml_out = yaml.load(out)
        # Some versions of salt have grains/pillars in a "local" key . . .
        if yaml_out.get('local'):
            return yaml_out['local']
        else:
            return yaml_out


def add_jinja_filters(filter_path='.'):

    filter_files = []
    added_filters = {}

    # Find py files and turn then into filterpath/blah/filter.py
    for e in os.walk(filter_path, followlinks=True):
        for f in e[2]:
            if f.endswith('py'):
                app.logger.debug("Adding debug %s" % os.path.join(e[0], f))
                app.logger.info("Adding info %s" % os.path.join(e[0], f))
                app.logger.warning("Adding warning %s" % os.path.join(e[0], f))
                app.logger.error("Adding error %s" % os.path.join(e[0], f))
                print("Checking for filters  %s" % os.path.join(e[0], f))
                filter_files.append(os.path.join(e[0], f))
    app.logger.debug("All filters  %s" % sorted(filter_files))

    # Now look in the files for jinja filters
    #import ipdb; ipdb.set_trace()
    for jfilter in filter_files:
        print("Checking out file %s" % jfilter)
        with open(jfilter) as file:
            text = file.read()
        # see https://stackoverflow.com/questions/48759838/how-to-create-a-function-object-from-an-ast-functiondef-node
        tree = ast.parse(text)
        code = compile(tree, filename="poopy", mode="exec")
        code_namespace = {}
        try:
            # exec the code into it's own namespace where we can access it without it pollutins global
            exec(code, code_namespace)
        except KeyError as ke:
            print(f"Error exec'ing code: {code} - {ke}")
            app.logger.debug(f"Error exec'ing code: {code} - {ke}")
        except ModuleNotFoundError as mne:
            print(f"Error exec'ing code: {code} - {mne}")
            app.logger.debug(f"Error exec'ing code: {code} - {mne}")
        except NameError as ne:
            print(f"Error exec'ing code: {code} - {ne}")
            app.logger.debug(f"Error exec'ing code: {code} - {ne}")
        for thing in tree.body:
            # Here we check if the thing in the filter is a Function, then if it's a jinja_filter
            print("Checking out thing %s" % thing)
            try:
                if isinstance(thing, ast.FunctionDef) and 'jinja_filter' in [ x.func.id for x in thing.decorator_list ]:
                    func_name = thing.name
                    added_filters[func_name] = ast.get_docstring(thing)
                    # add filter to jinja
                    app.jinja_env.filters[func_name] = code_namespace[func_name]
            except AttributeError as ae:
                print(f"Error inspecting {thing} in {jfilter}")
                app.logger.debug(f"Error inspecting {thing} in {jfilter}")

    #import ipdb; ipdb.set_trace()
    # These are the added filters.  must add these name + doc strings to the html
    # Also do this for built-in jinja filters
    for f in sorted(added_filters):
        app.logger.warning("%s: %s" % (f, added_filters[f]))
        doc_string = str(added_filters.get(f, 'No Description'))
        doc_string = doc_string.split('\n')[0]
        print("%s: %s" % (f, doc_string))


if __name__ == "__main__":
    app.debug = True
    add_jinja_filters(jinja_filter_path)
    app.run(host='0.0.0.0')
