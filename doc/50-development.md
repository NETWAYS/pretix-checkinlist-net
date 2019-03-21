# Development

## Requirements

### macOS

```
brew install python3 pandoc
```

### Pretix setup

```
python3 -m venv env
source env/bin/activate
pip3 install -U pip setuptools
export CXX=clang++
export CC=clang
cd src/
pip3 install -r requirements.txt -r requirements/dev.txt
```

### Local server

```
cd $HOME/coding/testing/pretix/pretix

source env/bin/activate

cd src

python3 manage.py collectstatic --noinput
python3 manage.py makemigrations
python3 manage.py migrate
python3 make_testdata.py
python3 manage.py runserver
```

http://127.0.0.1:8000/control admin@localhost - admin

## Plugin setup

```
cd $HOME/coding/netways/pretix/pretix
source env/bin/activate
cd $HOME/coding/netways/pretix/pretix-invoice-net
```

```
python3 setup.py install
```

## Plugin Release

```
VERSION=2.0.1
```

### Create release

```
sed -i "s/version = '.*'/version = '$VERSION'/g" setup.py
sed -i "s/archive\/.*'/archive\/v$VERSION.tar.gz'/g" setup.py
 
vim */__init__.py
 
     version = '...'

git commit -av -m "Release v$VERSION"

git tag -s -m "Version $VERSION" v$VERSION
 
git push
git push --tags
```


### PyPi Upload


```
python3 setup.py sdist
```

#### Test

```
python3 -m twine upload dist/pretix-checkinlist-net-$VERSION.tar.gz --verbose -r testpypi
```

#### Release

```
python3 -m twine upload dist/pretix-checkinlist-net-$VERSION.tar.gz --verbose
```

#### Requirements

```
pip3 install twine
```

```
cat >$HOME/.pypirc <<EOF

[distutils]
index-servers =
  pypi
  pypitest

[pypi]
repository=https://upload.pypi.org/legacy/
username=netways
password=XXX

[testpypi]
repository=https://test.pypi.org/legacy/
username=netways
password=XXX
EOF

chmod 600 ~/.pypirc
```
