### Release instructions


To create a release of hologram you will need fishtown permissions set up in your `~/.pypirc`.

```bash
bumpversion patch --commit --tag --new-version ${NEW_VERSION}
python setup.py sdist bdist_wheel
TGZ_PATH="dist/hologram-${NEW_VERSION}.tar.gz"
WHL_PATH="dist/hologram-${NEW_VERSION}-py3-none-any.whl"
twine check $TGZ_PATH $WHL_PATH
twine upload --repository pypitest $TGZ_PATH $WHL_PATH
git push && git push --tags
twine upload $TGZ_PATH $WHL_PATH
```
