#!/bin/sh
#    Copyright (c) 2013 Mirantis, Inc.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.
#
#    CentOS script.

LOGLVL=1
SERVICE_CONTENT_DIRECTORY=`cd $(dirname "$0") && pwd`
PREREQ_PKGS="wget make git python-pip python-devel"
PIPAPPS="pip python-pip pip-python"
PIPCMD=""
SERVICE_SRV_NAME="python-muranoclient"
GIT_CLONE_DIR=`echo $SERVICE_CONTENT_DIRECTORY | sed -e "s/$SERVICE_SRV_NAME//"`
# Functions
# Loger function
log()
{
        MSG=$1
        if [ $LOGLVL -gt 0 ]; then
                echo "LOG:> $MSG"
        fi
}

# Check or install package
in_sys_pkg()
{
        PKG=$1
        rpm -q $PKG > /dev/null 2>&1
        if [ $? -eq 0 ]; then
            log "Package \"$PKG\" already installed"
        else
                log "Installing \"$PKG\"..."
                yum install $PKG --assumeyes > /dev/null 2>&1
                if [ $? -ne 0 ];then
                        log "installation fails, exiting!!!"
                        exit
                fi
        fi
}

# find pip
find_pip()
{
        for cmd in $PIPAPPS
        do
                _cmd=$(which $cmd 2>/dev/null)
                if [ $? -eq 0 ];then
                        break
                fi
        done
        if [ -z $_cmd ];then
                echo "Can't find \"pip\" in system, please install it first, exiting!"
                exit 1
        else
                PIPCMD=$_cmd
        fi
}

# git clone
gitclone()
{
        FROM=$1
        CLONEROOT=$2
        log "Cloning from \"$FROM\" repo to \"$CLONEROOT\""
        cd $CLONEROOT && git clone $FROM > /dev/null 2>&1
        if [ $? -ne 0 ];then
            log "cloning from \"$FROM\" fails, exiting!!!"
            exit
        fi
}

# install
inst()
{
CLONE_FROM_GIT=$1
# Checking packages
        for PKG in $PREREQ_PKGS
        do
                in_sys_pkg $PKG
        done
# Find python pip
        find_pip
# If clone from git set
        if [ ! -z $CLONE_FROM_GIT ]; then
# Preparing clone root directory
        if [ ! -d $GIT_CLONE_DIR ];then
                log "Creating $GIT_CLONE_DIR directory..."
                mkdir -p $GIT_CLONE_DIR
                if [ $? -ne 0 ];then
                        log "Can't create $GIT_CLONE_DIR, exiting!!!"
                        exit
                fi
        fi
# Cloning from GIT
                GIT_WEBPATH_PRFX="https://git.openstack.org/cgit/openstack/"
                gitclone "$GIT_WEBPATH_PRFX$SERVICE_SRV_NAME.git" $GIT_CLONE_DIR
# End clone from git section
        fi
# Setupping...
        log "Running setup.py"
        MRN_CND_SPY=$SERVICE_CONTENT_DIRECTORY/setup.py
        if [ -e $MRN_CND_SPY ]; then
                chmod +x $MRN_CND_SPY
                log "$MRN_CND_SPY output:_____________________________________________________________"
## Setup through pip
                # Creating tarball
                rm -rf $SERVICE_CONTENT_DIRECTORY/*.egg-info
                cd $SERVICE_CONTENT_DIRECTORY && python $MRN_CND_SPY egg_info
                if [ $? -ne 0 ];then
                        log "\"$MRN_CND_SPY\" egg info creation FAILS, exiting!!!"
                        exit 1
                fi
                rm -rf $SERVICE_CONTENT_DIRECTORY/dist/*
                cd $SERVICE_CONTENT_DIRECTORY && python $MRN_CND_SPY sdist
                if [ $? -ne 0 ];then
                        log "\"$MRN_CND_SPY\" tarball creation FAILS, exiting!!!"
                        exit 1
                fi
                # Running tarball install
                TRBL_FILE=$(basename `ls $SERVICE_CONTENT_DIRECTORY/dist/*.tar.gz`)
                $PIPCMD install $SERVICE_CONTENT_DIRECTORY/dist/$TRBL_FILE
                if [ $? -ne 0 ];then
                        log "$PIPCMD install \"$TRBL_FILE\" FAILS, exiting!!!"
                        exit 1
                fi
        else
                log "$MRN_CND_SPY not found!"
        fi
}

# uninstall
uninst()
{
        # Uninstall trough  pip
        find_pip
        # looking up for python package installed
        PYPKG="muranoclient"
        _pkg=$($PIPCMD freeze | grep $PYPKG)
        if [ $? -eq 0 ]; then
                log "Removing package \"$PYPKG\" with pip"
                $PIPCMD uninstall $_pkg --yes
        else
                log "Python package \"$PYPKG\" not found"
        fi
}
# Command line args'
COMMAND="$1"
case $COMMAND in
        install )
                inst
                ;;

        installfromgit )
                inst "yes"
                ;;

        uninstall )
                log "Uninstalling muranoclient \"$SERVICE_SRV_NAME\" from system..."
                uninst
                ;;

        * )
                echo -e "Usage: $(basename "$0") command \nCommands:\n\tinstall - Install $SERVICE_SRV_NAME software\n\tuninstall - Uninstall $SERVICE_SRV_NAME software"
                exit 1
                ;;
esac

