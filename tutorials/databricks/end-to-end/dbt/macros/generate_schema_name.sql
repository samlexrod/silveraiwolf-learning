{#-
  Use the custom schema name VERBATIM (so `+schema: bronze` lands in `bronze`, not `silver_bronze`).
  Without this, dbt prefixes the target schema onto custom schemas. Falls back to the profile schema
  when a model sets none.
-#}
{% macro generate_schema_name(custom_schema_name, node) -%}
  {%- if custom_schema_name is none -%}
    {{ target.schema }}
  {%- else -%}
    {{ custom_schema_name | trim }}
  {%- endif -%}
{%- endmacro %}
