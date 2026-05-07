{
  description = "Ansible Collection for Dynu DNS";

  inputs = {
    nixpkgs.url = "github:nixos/nixpkgs/nixos-unstable";
  };

  outputs =
    { nixpkgs, ... }:
    let
      system = "x86_64-linux";
      pkgs = nixpkgs.legacyPackages.${system};
    in
    {

      devShells.${system}.default = pkgs.mkShell {
        name = "ansible-dynu-dns";
        packages = with pkgs; [
          ansible
          yq
        ];
      };
    };
}
