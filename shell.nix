with import <nixpkgs> {};

let
  pyduktape = python3Packages.buildPythonPackage rec {
    pname = "pyduktape";
    version = "0.0.6";
    doCheck = false;
    propagatedBuildInputs = with python3Packages; [ cython ];
    src = python3Packages.fetchPypi {
      inherit pname version;
      sha256 = "1g1k4m5k11nfsnljn5c042zdsbrmv5r4x8g1wkny8mj48jgksqg1";
    };
  };
in stdenv.mkDerivation rec {
  name = "dynastyscraper-environment";

  buildInputs = with python3Packages; [
    beautifulsoup4
  ] ++ [
    parallel
    duktape
    pyduktape
  ];
  nativeBuildInputs = [ zip wget ];
}
