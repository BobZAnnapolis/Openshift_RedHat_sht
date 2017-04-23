#!/bin/bash

dmn="osov4test"
rhc domain-create -n $dmn

appNum=0
appPrefix="app"

echo ""
echo "BUILDING ALL POSSIBLE APPS COMBINATIONS..."
echo ""

echo "...building just 1 jenkins-server"
(( appNum++ ))
appName="$appPrefix$appNum"
echo "rhc app-create" $appName jenkins-1 "-n" $dmn

scalingOptions=("--scaling --no-scaling")
for scaling in ${scalingOptions[@]}
do
    regions=("georgia texas")
##  regions=("georgia")
    for rgn in ${regions[@]}
    do
        regionToUse="--region "$rgn
##      regionToUse=""
##      echo $regionToUse
        gears=("small medium large xpaas")
##      gears=("small")
        for gear in ${gears[@]}
        do

            bldOpts="--no-git --no-dns $regionToUse $gearToUse $scaling"

            gearToUse="-g "$gear
##          echo $gearToUse
##          webcarts=$(rhc cartridges | grep web | sort | awk '{print $1}')
            webcarts=("diy-0.1 jbossews-1.0 jbossews-2.0 nodejs-0.10 perl-5.10 php-5.3 php-5.4 python-2.6 python-2.7 python-3.3 ruby-1.8 ruby-1.9 ruby-2.0")
            for web in ${webcarts[@]}
            do
##              DIY cartridges CANNOT be scaled
##              can only have 1 JENKINS server
##              XPAAS gears can ONLY have JBOSS apps
##              check for these conditions
                if [[ "$web" == *"diy"* && "$scaling" == "--scaling" ]] || \
                   [[ "$web" == *"jenkins-1"* ]] || \
                   [[ "$web" == *"jboss"* && "$gear" != "xpaas"  ]] || \
                   [[ "$web" != *"jboss"* && "$gear" == "xpaas"  ]]; then
                    echo "SKIPPING : " $web $rgn $gearToUse $scaling
##                  read -p "$*"
                else
##                  generate the list of non-web cartridges to use
##                   
##                  the quickest way to do this is manually. the current list of addons are
##                  divided up between db-related and other categories. there is no quick
##                  way to parse the cartridge names and additional info in order to
##                  extract the proper info to build the following arrays
##
                    addons=("empty cron-1.4 jenkins-client-1")
                    for addon in ${addons[@]}
                    do
                        if [[ "$addon" == *"empty"* ]]; then
                            addon=""
                        fi
##
##                      build the list of db-related cartridges to use
##                      phpmyadmin can ONLY be used when a db cartridge is a MYSQL version
                        dbs=("empty mongodb-2.4 mysql-5.1 mysql-5.5 postgresql-8.4 postgresql-9.2")
                        mysqlplus="phpmyadmin-4"
                        for db in ${dbs[@]}
                        do
                            if [[ "$db" == *"empty"* ]]; then
                                db=""
                            fi
##
##                          now that we are finally here, just loop every combination
                            (( appNum++ ))
                            appName="$appPrefix$appNum"
                            echo "rhc app-create" $appName $web $addon $db $bldOpts
##                          rhc app-create $appName $web $addon $db $bldOpts
                            if [[ "$db" == *"mysql"* ]]; then
                                (( appNum++ ))
                                appName="$appPrefix$appNum"
                                echo "rhc app-create" $appName $web $addon $db $mysqlplus $bldOpts
##                              rhc app-create $appName $web $addon $db $mysqlplus $bldOpts
                            fi
                        done
                    done ## addons
                fi ## check for invalid cart combinations
            done ## web cartridges
        done ## gears
    done ## regions
done ## scaling

