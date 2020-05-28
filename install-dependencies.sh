#!/usr/bin/env bash

set -o nounset
set -o errexit

## update list of available packages
echo "INFO: updating list of available packages"
apt-get -qq update || {
    echo "ERROR: failed updating list of available packages"
    exit 1
}

## download hugo c0.50 binary
(cd /var/tmp && curl -LO https://github.com/gohugoio/hugo/releases/download/v0.50/hugo_0.50_Linux-64bit.deb)
(dpkg -i /var/tmp/hugo_0.50_Linux-64bit.deb && rm -f /var/tmp/hugo_0.50_Linux-64bit.deb)

## use rvm to setup a ruby environment: https://rvm.io/
set +o nounset
set +o errexit

echo "INFO: setting up rvm environment"
source "$HOME/.rvmrc"
source "$rvm_path/scripts/rvm"
export PATH="${PATH:+${PATH}:}$rvm_bin_path"
echo "INFO: finished setting up rvm environment"

echo "INFO: changing to rvm default ruby"
rvm use default
echo "INFO: finished changing to rvm default ruby"

set -o nounset
set -o errexit

## install HTMLProofer
echo "INFO: installing HTMLProofer"
NOKOGIRI_USE_SYSTEM_LIBRARIES=true gem install --source https://rubygems.org html-proofer || {
    echo "ERROR: failed installing HTMLProofer"
    exit 1
}

exit 0

