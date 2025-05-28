cwlVersion: v1.0

$namespaces:
  s: https://schema.org/
s:softwareVersion: 0.1.0
schemas:
- http://schema.org/version/9.0/schemaorg-current-http.rdf


$graph:

- class: Workflow
  doc: Applies s expressions to EO acquisitions, including CEDA datasets
  id: ceda-snuggs
  requirements:
  - class: ScatterFeatureRequirement
  inputs:
    input_reference:
      doc: Input product reference
      label: Input product reference
      type: string[]
    s_expression:
      doc: s expression
      label: s expression
      type: string[]
    assets:
      doc: Assets required for processing
      label: Assets for processing
      type: string[]?
  label: s expressions
  outputs:
  - id: wf_outputs
    outputSource:
    - stac_join/results
    type: Directory

  steps:
    s_expr:
      in:
        input_reference: input_reference
        s_expression: s_expression
        assets: assets
      out:
      - results
      run: '#clt'
      scatter: [input_reference, s_expression]
      scatterMethod: flat_crossproduct
    stac_join:
      in:
        stac_catalog_dir:
          source: s_expr/results
      out:
        - results
      run: '#stac_join'


- baseCommand: ["s-expression", "calculate"]
  class: CommandLineTool

  id: clt

  arguments:
  - --input_reference
  - valueFrom: $( inputs.input_reference )
  - --s-expression
  - valueFrom: ${ return inputs.s_expression.split(":")[1]; }
  - --cbn
  - valueFrom: ${ return inputs.s_expression.split(":")[0]; }
  - --assets
  - valueFrom: | 
                $(inputs.assets ? inputs.assets.join(" ") : null)
  
  inputs:
    input_reference:
      type: string
    s_expression:
      type: string
    assets:
      type: string[]?

  outputs:
    results:
      outputBinding:
        glob: .
      type: Directory
  requirements:
    EnvVarRequirement:
      envDef:
        PATH: /srv/conda/envs/env_app_snuggs/bin:/srv/conda/bin:/srv/conda/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
    ResourceRequirement:
      ramMin: 10240
      coresMin: 3
    InlineJavascriptRequirement: {}
    DockerRequirement:
      dockerPull: public.ecr.aws/eodh/ceda-snuggs:0.1.0

- baseCommand: ["s-expression", "join"]
  class: CommandLineTool
  id: stac_join
  requirements:
    ResourceRequirement:
      coresMax: 2
      ramMax: 4096
  hints:
    DockerRequirement:
      dockerPull: public.ecr.aws/eodh/ceda-snuggs:0.1.0
  
  inputs:
    stac_catalog_dir:
      type:
        type: array
        items: Directory
        inputBinding:
          position: 1
          prefix: --stac_catalog_dir
  outputs:
    results:
      type: Directory
      outputBinding:
        glob: ./stac-join/