#!/bin/bash



V_DIR="venv"
which virtualenv 2>&1 > /dev/null
if [ $? -ne 0 ]; then
    echo "Please install virtualenv"
    exit 1
fi
[ -d $V_DIR ] || virtualenv -p python3 $V_DIR
source ./$V_DIR/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
SITE_DIR=$(python -c "import sys; print([ x for x in sys.path if x.endswith('site-packages') ][0])")
[ -h filters/salt ] || ln -s $SITE_DIR/salt/utils filters/salt
