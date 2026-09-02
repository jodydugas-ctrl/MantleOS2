# Hermes Delta Specimen

`upstream.lock.json` names the exact Hermes commit certified by the alpha
release. The source repository is not copied here.

Reconstruct the candidate NEST with:

```console
mantle assimilate github.com/nousresearch/hermes-agent --ref 30b83ab7b1f194503de9f5545d88c81c4db91e3f
```

The GitHub Release contains a generated bundle with the public `mantle/`
payload, the exact host-edge patch, checksums, test evidence, and SBOM. Runtime
identity and VCW state are intentionally absent.
