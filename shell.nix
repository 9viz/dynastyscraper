with import <nixpkgs> {};

stdenv.mkDerivation rec {
  name = "dynastyscraper-environment";

  buildInputs = with python3Packages; [
    beautifulsoup4
  ];
  nativeBuildInputs = [];
}
