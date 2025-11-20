# Http_req_smuggling
Cyber Offense and Defense Curse Project. This will be a rapresentation of the most important labs of HttpRS Port Swigger, explaining how this attack works.

HTTP request smuggling - 22 labs
Breve definizione: tecnica che sfrutta differenze nel parsing delle richieste HTTP tra
front-end (proxy, load-balancer) e back-end per “infiltrare” una richiesta nascosta nel flusso;
può consentire cache poisoning, session hijacking, bypass di filtri e altro. PortSwigger offre
un ampio set di lab (topic avanzato) per comprendere CL.TE vs TE.CL,
chunking/Content-Length inconsistencies e come costruire request smuggled. Competenze:
formattazione raw HTTP, timing, diagnosi parsing differences, mitigazioni a livello proxy
