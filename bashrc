# Bash .profile script for inside our container
#
# Version 2020-07-22

if [ -f /etc/bashrc ]; then
  . /etc/bashrc
fi

export PS1="\\u@\\h:\\w\\$ "

alias lal='ls -al'
alias ll='ls -l'
alias pd='pushd .'
alias e='edit'

if alias rm > /dev/null 2> /dev/null; then unalias rm; fi
if alias mv > /dev/null 2> /dev/null; then unalias mv; fi
if alias cp > /dev/null 2> /dev/null; then unalias cp; fi
alias nslookup='nslookup -sil'


###
## Shortcuts for grepping code
#

function g_base { grep "$2" ${@:3} --include=*.py --include=*.scss --include=*.html --include=*.md --include=*.txt --exclude=*/migrations/* --exclude=_graveyard/* "$1" *; }

function g { clear; g_base "$1" -RIip; }
export g

function gi { clear; g_base "$1" -RIp; }
export gi

function gj { clear; g_base "$1" -RIip --include=\*.js --include=\*.jsx --include=\*.json --exclude=\*.min.js; }
export gj

function gij { clear; g_base "$1" -RIp --include=\*.js --include=\*.jsx --include=\*.json --exclude=\*.min.js; }
export gij

function ge { g_base "$1" -RIip | sed 's/:.*//' | sort | uniq | tr '\n' '\0' | xargs -0 edit; }
export ge

function gie { g_base "$1" -RIp | sed 's/:.*//' | sort | uniq | tr '\n' '\0' | xargs -0 edit; }
export gie

function gje { g_base "$1" -RIip --include=\*.js --include=\*.jsx --include=\*.json --exclude=\*.min.js | sed 's/:.*//' | sort | uniq | tr '\n' '\0' | xargs -0 edit; }
export gje

function gije { g_base "$1" -RIp --include=\*.js --include=\*.jsx --include=\*.json --exclude=\*.min.js | sed 's/:.*//' | sort | uniq | tr '\n' '\0' | xargs -0 edit; }
export gije


###
## Internal Helpers
#

# Helper to add chunks to the path exactly once
function _addToPath {
  if [ $# != 1 ]; then echo 'Internal Error'; return; fi
  printenv PATH | grep -q -e "^$1:" -e ":$1:" -e ":$1$"
  if [ $? != 0 ]; then
    export PATH="$1:$PATH"
  fi
}


###
## Jumping Around the Environment
#

PYTHON_PKGS=/usr/local/lib/python3.7/site-packages

function j {
  if [ $# != 1 ]; then
    echo 'Jump script requires a jump target.'
    return
  fi
  case "$1" in
    p)
      cd ${PYTHON_PKGS}
      ;;
    pd)
      cd ${PYTHON_PKGS}/django/
      ;;
    pda)
      cd ${PYTHON_PKGS}/django/contrib/admin/templates/admin
      ;;
    *)
      echo 'Unrecognized jump target.'
      ;;
  esac
}
export j
