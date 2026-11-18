# explorer · FIX-005

- **Fecha:** 2026-11-18
- **Veredicto:** ok

## Respuesta
commit_feature (git_agent.py:326-413): guard -> exige id/title -> next_version = _next_patch_version() -> doc_agent.bump_version -> doc_agent.update_changelog(feature_id=id) -> git add -A -> git commit. Si el commit falla (393-398) devuelve AgentResult(False) con message + warnings, sin needs y sin rollback. No ejecuta uv lock. No existe helper de restauracion; el reintento no es idempotente.

## Donde esta
- agents/agents/git_agent.py:326 def commit_feature; :354 next_version; :376-381 bump; :383-387 changelog; :389 add -A; :393-398 fallo sin rollback
- agents/agents/git_agent.py:415-425 _next_patch_version: regex sobre el pyproject actual, no sobre la version commiteada
- agents/agents/documentation_agent.py:76-120 update_changelog (no existe write_changelog); :89-101 construye la entrada por feature_id; :122-140 _insert_changelog inserta tras el marker \n---\n sin comprobar duplicados
- agents/agents/documentation_agent.py:174-225 bump_version: pyproject, badge README y linea de version; avisa si no encuentra badge o linea
- agents/tests/conftest.py:14-41 fixture project_root/context con git init real; test_git_commit_feature.py:8-15 _write_versioned_files; ningun test mockea git, todos usan subprocess real
- agents/tools/git_tool.py:40-47 _git y status_porcelain; no hay metodos checkout ni restore
- agents/agents/dependency_agent.py:133-156 unico uv lock --check (run_command, cwd, MissingDependencyError/ToolExecutionError)

## Verificado en copia TEMP
Secuencia: copia del repo sin .git/.venv, git init + commit setup, hook .git/hooks/pre-commit con exit 1, llamada commit_feature(FIX-999) con HARNESS_ASSUME_YES=1.
run1: success=false, message git commit fallo (stderr vacio), warnings solo la linea de version ausente del README, needs=[].
Estado run1: version 0.1.6, badge 0.1.6, 1 bloque Unreleased con FIX-999, git status M CHANGELOG/README/pyproject ya en el index, log solo chore setup, uv.lock intacto.
run2 mismo id: version 0.1.7, 2 bloques Unreleased identicos, 2 entradas FIX-999, todo staged, cero commits.
Conclusion: el fallo deja el arbol sucio y staged, no revierte nada, no pide accion al usuario, y reintentar acumula bumps y duplica el CHANGELOG.

## Puntos a cambiar
- git_agent.py:393-398: en el fallo, restaurar pyproject/README/CHANGELOG (git checkout -- ficheros, o snapshot previo en memoria) y devolver needs con la causa; hoy solo devuelve message.
- git_agent.py:354 y :415-425: derivar next_version de la version commiteada (git show HEAD:pyproject.toml) para que un reintento no sume otro patch.
- documentation_agent.py:89-101: antes de insertar, buscar (feature_id) en CHANGELOG.md y devolver success sin escribir si ya esta.
- git_agent.py:389: add -A arrastra cambios ajenos al cierre; acotar a pyproject, README y CHANGELOG.
- AgentResult(False, ..., needs=[...]) es el patron correcto para pedir accion: ya se usa en git_agent.py:344-349 y en la puerta de permisos (base_agent.py:134-143).

## Sin verificar
- No probe el caso update_changelog falla y commit si funciona, ni el rollback parcial.
- No pase por la CLI real con --yes; use HARNESS_ASSUME_YES=1 porque run() sin autorizacion se corta antes en la puerta de permisos.
- No revise consumidores de commit_feature fuera de agents/tests; FIX-005 no existe aun en harness/featureslist.json.
- Para un test nuevo que fuerce el fallo: no hay precedente; opciones son hook pre-commit temporal o monkeypatch de GitTool.commit devolviendo ProcessResult(returncode=1). ProcessResult esta en agents/tools/process_tool.py.
