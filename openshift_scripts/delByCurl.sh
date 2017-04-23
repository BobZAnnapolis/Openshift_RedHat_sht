#!/bin/bash

##dmns=$(rhc domains | grep Domain | awk '{print $2}')
dmns="osov4test"

echo ""
echo "DELETING APPS..."
echo ""
for dmn in $dmns
do
    echo ""
    echo "...gathering apps in Domain : ${dmn}..."
    echo ""
    apps=$(rhc apps | grep uuid | grep ${dmn} | awk '{print $1}')
    for app in $apps
    do 
        ##echo "rhc app-delete ${app} -n ${dmn} --confirm"
        ##rhc app-delete ${app} -n ${dmn} --confirm
	echo "curl -k -X DELETE https://blah-aio01.dudeshift.partshop.lab24.co/broker/rest/domain/osov4test/application/${app} -u 'demo:demo' &"
	curl -k -X DELETE https://blah-aio01.dudeshift.partshop.lab24.co/broker/rest/domain/osov4test/application/${app} -u "demo:demo" &
	echo "  "
	echo "  "
    done
done

echo ""
echo "DELETING KEYS in HOSTFILE..."
echo ""
for dmn in $dmns
do
    keys=$(cat ~/.ssh/known_hosts | grep ${dmn} | awk '{print $1}')
    for key in $keys
    do 
        echo "ssh-keygen -R ${key}"
        ssh-keygen -R ${key}
    done
done

echo ""
echo "DELETING ~/oso-tests/..."
echo ""
echo "rm -fR ~/oso-tests/"
rm -fR ~/oso-tests/

