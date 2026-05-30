import sys, tempfile, yaml, os
from pathlib import Path
sys.path.insert(0, 'src')
from sim_agent.core.template_store import TemplateStore
from sim_agent.core.experience_store import ExperienceStore
from sim_agent.adapters.base_parser import BasePaperParser
from sim_agent.adapters.base_diagnostics import BaseDiagnostics, ResultValidator
from sim_agent.adapters.mcp_wizard import McpWizard, create_profile_quick
from sim_agent.adapters.model_learner import ModelLearner

# 1 TemplateStore
print('--- 1. TemplateStore ---')
d = tempfile.mkdtemp(); td = Path(d); (td / 's').mkdir()
y = {'meta': {'name': 'Cantilever', 'domain': 'structural', 'physics_type': 'solid_mechanics', 'dimension': '3D', 'common_pitfalls': ['missing constraint']}, 'geometry': {'length': {'symbol': 'L', 'default': 1.0}, 'width': {'symbol': 'W', 'default': 0.1}}, 'physics': {'interface': 'Static'}, 'study': {'type': 'stationary'}}
with open(td / 's' / 'beam.yaml', 'w') as f: yaml.dump(y, f)
st = TemplateStore(td)
assert st.load_all() == 1
assert st.match({'domain': 'structural'}) is not None
assert st.match({'domain': 'nonexistent'}) is None
t = st.get('Cantilever')
p = t.extract_parameters()
assert 'L' in p and 'W' in p
print('  PASS: params=' + str(list(p.keys())) + ', domains=' + str(st.list_domains()))

# 2 ExperienceStore
print('--- 2. ExperienceStore ---')
d2 = tempfile.mkdtemp()
es = ExperienceStore(Path(d2) / 'e.json')
assert es.count == 0
e = es.record_correction('s', 't', 's', 'c', 'f')
assert es.count == 1 and len(es.find_by_domain('s')) == 1
assert len(es.find_relevant('s', ['s'])) == 1
assert len(es.find_relevant('s', ['nope'])) == 0
es.verify(e.id)
assert es.get(e.id).verified_count == 1
es2 = ExperienceStore(Path(d2) / 'e.json')
assert es2.count == 1
print('  PASS: count=' + str(es.count))

# 3 BasePaperParser
print('--- 3. BasePaperParser ---')
class PP(BasePaperParser):
    DOMAIN_KEYWORDS = {'structural': ['stress', 'FEA'], 'thermal': ['heat']}
    PHYSICS_KEYWORDS = {'solid': ['stress', 'elastic'], 'heat': ['thermal']}
    NUMERIC_PATTERNS = [(r'L\s*[=＝]\s*(\d+\.?\d*)\s*(m)', 'length', 'length')]
pp = PP()
r = pp.parse(text='3D FEA stress analysis stationary. L=1m.')
assert r.domain == 'structural', 'domain: ' + r.domain
assert r.study_type == 'stationary', 'study: ' + r.study_type
assert r.dimension == '3D', 'dim: ' + r.dimension
assert 'length' in r.geometry_params, 'params: ' + str(r.geometry_params)
r2 = pp.parse(text='some random text about nothing')
assert r2.domain == 'unknown'
assert len(r2.missing_info) > 0
print('  PASS: domain=' + r.domain + ', study=' + r.study_type + ', params=' + str(r.geometry_params))

# 4 BaseDiagnostics
print('--- 4. BaseDiagnostics ---')
class D(BaseDiagnostics):
    ERROR_PATTERNS = [(r'rigid', 'rigid', 'Add constraint'), (r'no conv', 'conv', 'Refine')]
d = D()
r = d.diagnose({'success': False, 'error': 'rigid body motion'})
assert r.quality_score == 0 and r.details['error_code'] == 'rigid'
r = d.diagnose({'success': True})
assert r.quality_score == 1.0
r = d.diagnose({'success': False, 'error': 'some weird unknown error'})
assert r.suggestions and r.details.get('error_code') is None
v = ResultValidator()
r = v.compare({'x': 105}, {'x': {'value': 100, 'tolerance': 0.1}})
assert r['all_match']
r = v.compare({'x': 200}, {'x': {'value': 100, 'tolerance': 0.1}})
assert not r['all_match']
print('  PASS')

# 5 McpWizard
print('--- 5. McpWizard ---')
w = McpWizard()
ans = {'software_name': 'ANSYS', 'python_sdk': 'pyansys', 'sdk_install': 'pip', 'connection_mode': '1', 'domain_count': 's,t', 'error_count': 'e1,e2', 'template_count': 't1,t2', 'keywords_per_domain': 'k1,k2', 'core_tools': 'c1,c2'}
while True:
    q = w.get_next_question()
    if q is None: break
    w.answer(q['step_id'], q['question']['id'], ans.get(q['question']['id'], 'x'))
assert w.profile.config_complete
assert w.profile.name == 'ANSYS' and w.profile.connection_mode == 'sdk'
plan = w.generate_file_plan()
assert 'files_to_create' in plan and 'codex_mcp_config' in plan
qp = create_profile_quick('QS', 'q', 'pip', 'cli')
assert qp.name == 'QS'
print('  PASS: profile=' + w.profile.name)

# 6 ModelLearner
print('--- 6. ModelLearner ---')
ml = ModelLearner()
assert '.py' in ml.supported_formats() and '.mph' in ml.supported_formats()
tf = tempfile.NamedTemporaryFile(suffix='.py', mode='w', encoding='utf-8', delete=False)
tf.write('import mph\n')
tf.write('a = 1e-6\n')
tf.write('R = 0.2*a\n')
tf.write('epsilon_rod = 11.7\n')
tf.write('physics = comp.physics().create("ewfd", "ElectromagneticWavesFrequencyDomain")\n')
tf.write('pbc = physics.create("pbc1", "PeriodicCondition")\n')
tf.write('eig = study.create("eig1", "Eigenfrequency")\n')
tf.close()
r = ml.learn_from(tf.name)
assert r['success']
e = r['extracted']
assert e.study_type == 'eigenfrequency'
assert e.physics_type == 'electromagnetic_waves'
assert len(e.boundary_conditions) >= 1
assert 'a' in e.geometry_params
os.unlink(tf.name)
print('  PASS: study=' + e.study_type + ', physics=' + e.physics_type)

print()
print('===== sim-agent-platform: 6/6 PASSED =====')