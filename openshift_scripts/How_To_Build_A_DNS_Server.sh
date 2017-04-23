##
## How to install DNS on an OpenShift Origin Broker
## ================================================
##
## It is a summary of information from "2.1 DNS" in "2. Preparing the Broker Host System" in 
## the https://docs.openshift.org/origin-m4/oo_deployment_guide_comprehensive.html#preparing-the-broker-host-system
##
## the steps were performed early November 2015 against a MASH vm built at NetCraft using the "Mike RDO CentOS 6.6" image in the "PartShop" project, "region1"
##
##
## PRE-REQUISITES :
##	create MASH VM
##		CURRENT PROJECT : PartShop
##		IMAGE : Mike RDO CentOS 6.6
##		CURRENT REGION : region1
##		associate a floating IP
##			this will be a 10.0 address - this is the 'ip address' to use below
##	from a terminal session :
##		ssh-copy-id centos@above_ip
##		
## start here & perform after you c an ssh / puty into the new vm
## perform as root
##
sudo -i
##
## In order for OpenShift Origin to work correctly, you will need to configure BIND 
## so that you have a DNS server setup.
##
## In OpenShift Origin, name resolution is used primarily for communication between our 
## broker and node hosts. It is additionally used for dynamically updating the DNS 
## server to resolve gear application names when we start creating application gears.
##
## To proceed, ensure that bind and the bind utilities have been installed on the broker host:
## reboot to set up the /etc/sysconfig/network file
##
domain=test.dns.server
hname=${hostname}  <- get the hostname from cmd line and save in local var
sed -i "s/HOSTNAME=.*$/HOSTNAME=${hname}.${domain}/" /etc/sysconfig/network
hostname ${hname}.${domain}

yum clean all
yum -y update
yum -y install bind bind-utils httpd-tools vim wget git curl zip unzip
reboot
##
## Create DNS environment variables and a DNSSEC key file
##
## after reboot, re-init our session domain variable
##
domain=test.dns.server
##
## DNSSEC, which stands for DNS Security Extensions, is a method by which DNS servers 
## can verify that DNS data is coming from the correct place. You create a 
## private/public key pair to determine the authenticity of the source domain name 
## server. In order to implement DNSSEC on your new PaaS, you need to create a key 
## file, which will be stored in /var/named. For convenience, set the "$keyfile" 
## variable now to the location of the this key file:
##
keyfile=/var/named/${domain}.key
##
## Now create a DNSSEC key pair and store the private key in a variable 
## named "$KEY" by using the following commands:
##
pushd /var/named
rm K${domain}*
dnssec-keygen -a HMAC-MD5 -b 512 -n USER -r /dev/urandom ${domain}
KEY="$(grep Key: K${domain}*.private | cut -d ' ' -f 2)"
popd
echo $KEY
##
## You must also create an rndc key, which will be used by the init script to
## query the status of BIND when you run service named status:
## 
rndc-confgen -a -r /dev/urandom
##
## Configure the ownership, permissions, and SELinux contexts for the keys 
## that you’ve created:
##
restorecon -v /etc/rndc.* /etc/named.*
chown -v root:named /etc/rndc.key
chmod -v 640 /etc/rndc.key
##
## Create a /var/named/fowarders.conf file for host name resolution
##
## The DNS forwarding facility of BIND can be used to create a large site-wide 
## cache on a few servers, reducing traffic over links to external name servers. 
## It can also be used to allow queries by servers that do not have direct 
## access to the Internet, but wish to look up exterior names anyway. Forwarding 
## occurs only on those queries for which the server is not authoritative and 
## does not have the answer in its cache.
##
## Create the forwarders.conf file with the following commands:
##
cd /var/named/
echo "forwarders { 8.8.8.8; 8.8.4.4; } ;" >> /var/named/forwarders.conf
restorecon -v /var/named/forwarders.conf
chmod -v 640 /var/named/forwarders.conf
cat /var/named/forwarders.conf
##
## Configure subdomain resolution and create an initial DNS database
##
## To ensure that you are starting with a clean /var/named/dynamic directory, 
## remove this directory if it exists:
##
rm -rvf /var/named/dynamic
mkdir -vp /var/named/dynamic
##
## Issue the following command to create the ${domain}.db file (before running this 
## command, verify that the $domain variable that you set earlier is still available):
##
cd /var/named/dynamic
cat <<EOF > /var/named/dynamic/${domain}.db
\$ORIGIN .
\$TTL 1 ; 1 seconds (for testing only)
${domain}       IN SOA  ns1.${domain}. hostmaster.${domain}. (
            2011112904 ; serial
            60         ; refresh (1 minute)
            15         ; retry (15 seconds)
            1800       ; expire (30 minutes)
            10         ; minimum (10 seconds)
            )
        NS  ns1.${domain}.
        MX  10 mail.${domain}.
\$ORIGIN ${domain}.
ns1         A   127.0.0.1
EOF
##
## in above file, edit and remove extra lines {if necessary}
##
## Once you have entered the above echo command, cat the contents of the file to ensure
## that the command was successful:
##
cat /var/named/dynamic/${domain}.db
##
## Now we need to install the DNSSEC key for our domain
##
cat <<EOF > /var/named/${domain}.key
key ${domain} {
  algorithm HMAC-MD5;
  secret "${KEY}";
};
EOF
##
## Set the correct permissions and contexts:
##
chown -Rv named:named /var/named
restorecon -rv /var/named
##
## Create the /etc/named configuration file
##
## You will also need to create the named.conf file. Before running the following 
## command, verify that the $domain variable that you set earlier is still 
## available.
##
cd /etc
echo $domain
cat <<EOF > /etc/named.conf
// named.conf
//
// Provided by Red Hat bind package to configure the ISC BIND named(8) DNS
// server as a caching only nameserver (as a localhost DNS resolver only).
//
// See /usr/share/doc/bind*/sample/ for example named configuration files.
//

options {
    listen-on port 53 { any; };
    directory   "/var/named";
    dump-file   "/var/named/data/cache_dump.db";
    statistics-file "/var/named/data/named_stats.txt";
    memstatistics-file "/var/named/data/named_mem_stats.txt";
    allow-query     { any; };
    recursion yes;

    /* Path to ISC DLV key */
    bindkeys-file "/etc/named.iscdlv.key";

    // set forwarding to the next nearest server (from DHCP response
    forward only;
    include "forwarders.conf";
};

logging {
        channel default_debug {
                file "data/named.run";
                severity dynamic;
        };
};

// use the default rndc key
include "/etc/rndc.key";

controls {
    inet 127.0.0.1 port 953
    allow { 127.0.0.1; } keys { "rndc-key"; };
};

include "/etc/named.rfc1912.zones";

include "${domain}.key";

zone "${domain}" IN {
    type master;
    file "dynamic/${domain}.db";
    allow-update { key ${domain} ; } ;
};
EOF
## in above file, edit and remove extra lines {if necessary}
##
## set the permissions for the new configuration file that you just created:
##
chown -v root:named /etc/named.conf
restorecon /etc/named.conf
##
## Start the named service
##
## Now you are ready to start up your new DNS server and add some updates.
##
service named restart
##
## should see the following :
##	Stopping named:                                            [  OK  ]
##	Starting named:                                            [  OK  ]
##
##
## You should see the above confirmation message that the service was started correctly. 
## If you do NOT see an OK message, run through the above steps again and ensure that 
## the output of each command matches the contents of this document. If you are still 
## having trouble after trying the steps again, refer to your help options
##
##
##vim /etc/sysconfig/iptables and add a port 53 TCP rule 
####-A INPUT -m state --state NEW -m tcp -p tcp --dport 53 -j ACCEPT
##
cd /etc/sysconfig
vim /etc/sysconfig/iptables
	:
	: perform above edit and save
	:
service iptables restart
##
## should see the following :
##	iptables: Setting chains to policy ACCEPT: filter          [  OK  ]
##	iptables: Flushing firewall rules:                         [  OK  ]
##	iptables: Unloading modules:                               [  OK  ]
##	iptables: Applying firewall rules:                         [  OK  ]
##
##
##vim /var/named/dynamic/${domain}.db file and add A record
####eg: bobtest         A       10.0.133.45
##
cd /var/named/dynamic
vim /var/named/dynamic/${domain}.db
	:
	: <- perform above edits, save, use hostname and 10.0.* ip addr
	:
service named restart
##
## Configure host name resolution to use local BIND server
##
## Now you need to update the resolv.conf file to use the local named service that you 
## just installed and configured. Open up your /etc/resolv.conf file and add the following 
## entry as the first nameserver entry in the file:
##	nameserver 127.0.0.1
##
cd /etc
vim resolv.conf
##
## make sure named starts on boot and that firewall cfg'd to pass thru DNS traffic
##	lokkit adds a UDP Port 53 DNS rule into iptables
lokkit --service=dns
chkconfig named on
##
## Add the Broker Host to DNS
##
## If you configured and started a BIND server per this document, or you are working 
## against a BIND server that was already in place, you now need to add a record for 
## your broker node (or host) to BIND’s database. To accomplish this task, you will 
## use the nsupdate command, which opens an interactive shell. 
## Replace "broker.example.com" with your preferred hostname and "10.0.133.71" with 
## the ip address of the broker
##
## add the DNS record into BIND db
##	substitute ${hostname} w/real hostname - var substitution didn't work
cd /var/named
nsupdate -k $keyfile
server 127.0.0.1
update add ${hostname} 180 A 10.0.133.71
send
##
## once all of the above is complete, no error messages occurred and everything
## is running successfully - run the following to test communication functionality
##
## on another vm - use address of above machine
##
dig @10.0.133.71 yahoo.com
##
## on machines you want to talk to DNS
##	edit /etc/resolve
##	add nameserver 10.0.133.71 as 1st nameserver
##
## the following should now work from non-DNS machines w/modified /etc/resolv.conf
nslookup $(hostname)
##
