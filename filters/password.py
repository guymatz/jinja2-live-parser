from random import SystemRandom
import passlib.hash
import crypt
import string
import sys
import inspect

from ansible.errors import AnsibleError, AnsibleFilterError
from ansible.plugins.lookup import LookupBase
from ansible.utils.listify import listify_lookup_plugin_terms

try:
    import passlib.hash
    HAS_PASSLIB = True
except:
    HAS_PASSLIB = False

try:
    import bcrypt
except:
    pass

def _debug(msg):
    print("%s - %s" % (inspect.stack()[1][3], msg))

def create_encrypted_password(password, hashtype='sha512', salt=None, saltsize=None, ident=None, debug=False, **kwargs):

    """ Returns an encrypted string
  
    :param password: String to encrypt (Required)
    :param hashtype: Encryption Algorithm (default: sha512)
    :param salt: salt to supply to algorithm (default: None)
    :param saltsize: Length of randomly generated salt to supply to algorithm is none is provided (default: None)
    :param ident: Ident to supply to encryption algorithm.  I don't really know what this is (default: None)
    :param debug: Boolean (default: False)
 
    :return: string
    """
    
    cryptmethod = { }
    for h in [ x for x in dir(passlib.hash) if not x.startswith('_') ]:
        cryptmethod[h] = {}
        cryptmethod[h]['ident'] = getattr(eval('passlib.hash.%s' % h), 'ident', None)
        cryptmethod[h]['salt_size'] = getattr(eval('passlib.hash.%s' % h), 'default_salt_size', None)
        if debug:
            _debug("cryptmethod %s: %s" % (h, cryptmethod[h]) )

#    {
#        'md5': '1',
#        'blowfish': '2a',
#        'sha256': '5',
#        'sha512': '6',
#    }

    # hashtypes are sometimes named hashtype_crypt, e.g. sha1_crypt
    if cryptmethod.get(hashtype):
        print("%s exists" % hashtype)
    elif cryptmethod.get('%s_crypt' % hashtype):
        hashtype = '%s_crypt' % hashtype
        print("%s exists" % hashtype)
    else:
        raise AnsibleFilterError("I don't think I know about the hash %s (or %s_crypt)" % (hashtype, hashtype))


    if salt is None and cryptmethod.get('salt_size', False):
        r = SystemRandom()
        if cryptmethod[hashtype]['salt_size'] and not saltsize:
            saltsize = cryptmethod[hashtype]['salt_size']
        else:
            raise AnsibleFilterError('Unable to determine the salt size for hash %s. Please provide it' % hashtype)
        saltcharset = string.ascii_letters + string.digits + '/.'
        salt = ''.join([r.choice(saltcharset) for _ in range(saltsize)])

    if not HAS_PASSLIB:
        if sys.platform.startswith('darwin'):
            raise AnsibleFilterError('|encrypt_password requires the passlib python module to generate password hashes on Mac OS X/Darwin')
    if ident:
        pass
    elif cryptmethod[hashtype]['ident']:
        ident = cryptmethod[hashtype].get('ident')
    else:
        ident = ''

    if salt:
        kwargs['salt'] = "%s%s" % (ident, salt)

    #encrypted = crypt.crypt(password, saltstring)

    #import pdb; pdb.set_trace()
    try:
        cls = getattr(passlib.hash, hashtype)
        encrypted = cls.encrypt(password, **kwargs)
    except Exception as e:
        raise AnsibleError('Error encrypting password: %s' % e)

    _debug("Encrypted %s with %s and got %s" % (password, kwargs, encrypted))
    return encrypted

class FilterModule(object):
    def filters(self):
        return {
                'create_encrypted_password': create_encrypted_password
        }
