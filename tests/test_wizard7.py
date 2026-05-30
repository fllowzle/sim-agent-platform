# -*- coding: utf-8 -*-
import sys; sys.path.insert(0,'src')
from sim_agent.adapters.mcp_wizard import McpWizard
w = McpWizard()
answers = {'software_name':'T','python_sdk':'t','sdk_install':'t','connection_mode':'1',
           'domain_count':'a','error_count':'a','template_count':'a',
           'keywords_per_domain':'a','core_tools':'a',
           'guides_dir':'D:/my_docs/guides','pdf_dir':'D:/my_docs/pdf','pdf_relevance':'structural:[SA,MM]'}
c = 0
while True:
    q = w.get_next_question()
    if q is None: break
    c += 1
    w.answer(q['step_id'], q['question']['id'], answers.get(q['question']['id'], 'x'))
    print('Step', q.get('step','?'), ':', q['question']['id'], '=', str(answers.get(q['question']['id'], 'x'))[:30])
print('Total questions:', c)
print('Config complete:', w.profile.config_complete)
print('kb_guides_dir:', w.profile.kb_guides_dir)
print('kb_pdf_dir:', w.profile.kb_pdf_dir)
print('kb_relevance_map:', w.profile.kb_relevance_map)
plan = w.generate_file_plan()
print('Has knowledge_bridge in plan:', 'knowledge_bridge_config' in plan)
print('KB config in plan:', plan.get('knowledge_bridge_config', 'MISSING'))
print('OK')