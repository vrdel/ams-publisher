PKGNAME=ams-publisher
SPECFILE=${PKGNAME}.spec

PKGVERSION=$(shell grep -s '^Version:' $(SPECFILE) | sed -e 's/Version: *//')

srpm: dist
	rpmbuild -ts ${PKGNAME}-${PKGVERSION}.tar.gz

rpm: dist
	rpmbuild -ta ${PKGNAME}-${PKGVERSION}.tar.gz

dist:
	rm -rf dist build
	python3 setup.nagios.py custombuild
	mv -f dist/argo-nagios-${PKGNAME}-${PKGVERSION}.tar.gz argo-nagios-${PKGNAME}-${PKGVERSION}.tar.gz
	rm -rf dist build
	python3 setup.sensu.py custombuild
	mv -f dist/argo-sensu-${PKGNAME}-${PKGVERSION}.tar.gz argo-sensu-${PKGNAME}-${PKGVERSION}.tar.gz

sources: dist

clean:
	rm -rf *${PKGNAME}-${PKGVERSION}.tar.gz
	rm -f MANIFEST
	rm -rf build
	rm -rf dist
