"""Sample contract texts for testing."""

# Simple NDA for basic testing
SIMPLE_NDA = """
NON-DISCLOSURE AGREEMENT

1. CONFIDENTIALITY
The Receiving Party agrees to hold in confidence all Confidential Information
disclosed by the Disclosing Party for a period of five (5) years.

2. TERM
This Agreement shall remain in effect for a period of two (2) years from the
Effective Date.

3. GOVERNING LAW
This Agreement shall be governed by the laws of the State of Delaware.
"""

# Complex services agreement with multiple clause types
COMPLEX_SERVICE_AGREEMENT = """
MASTER SERVICES AGREEMENT

1. SERVICES
Provider shall perform the services described in Exhibit A ("Services") in
accordance with the terms of this Agreement.

2. PAYMENT TERMS
Client shall pay Provider within thirty (30) days of invoice receipt.
Late payments shall accrue interest at a rate of 1.5% per month.

3. LIMITATION OF LIABILITY
IN NO EVENT SHALL PROVIDER BE LIABLE FOR ANY INDIRECT, INCIDENTAL, SPECIAL,
CONSEQUENTIAL, OR PUNITIVE DAMAGES, REGARDLESS OF THE CAUSE OF ACTION.
Provider's total aggregate liability shall not exceed the fees paid by Client
in the twelve (12) months preceding the claim.

4. INDEMNIFICATION
Client shall indemnify, defend, and hold harmless Provider and its officers,
directors, and employees from any claims, damages, or expenses arising from
Client's use of the Services or breach of this Agreement.

5. INTELLECTUAL PROPERTY
All intellectual property rights in the Services and any deliverables shall
remain with Provider. Client receives only a limited, non-exclusive license
to use the deliverables for internal business purposes.

6. TERMINATION
Either party may terminate this Agreement with sixty (60) days written notice.
Provider may terminate immediately upon Client's failure to pay any invoice
within thirty (30) days of its due date.

7. WARRANTY
Provider warrants that the Services will be performed in a professional and
workmanlike manner consistent with industry standards. THIS WARRANTY IS
EXCLUSIVE AND IN LIEU OF ALL OTHER WARRANTIES, EXPRESS OR IMPLIED.

8. FORCE MAJEURE
Neither party shall be liable for any failure to perform due to causes beyond
its reasonable control, including but not limited to acts of God, war,
terrorism, strikes, or natural disasters.

9. DISPUTE RESOLUTION
Any dispute arising out of this Agreement shall be resolved through binding
arbitration in accordance with the rules of the American Arbitration
Association. The arbitration shall take place in New York, New York.

10. ASSIGNMENT
Neither party may assign this Agreement without the prior written consent of
the other party, except that either party may assign to an affiliate or in
connection with a merger or acquisition.

11. NOTICE
All notices shall be in writing and delivered by certified mail, return
receipt requested, or by recognized overnight courier to the addresses set
forth herein.

12. ENTIRE AGREEMENT
This Agreement constitutes the entire agreement between the parties and
supersedes all prior agreements, whether written or oral, relating to the
subject matter hereof.

13. SEVERABILITY
If any provision of this Agreement is held invalid or unenforceable, the
remaining provisions shall continue in full force and effect.

14. AMENDMENT
This Agreement may only be amended by a written instrument signed by both
parties.
"""

# Minimal contract for edge case testing
MINIMAL_CONTRACT = "Agreement between parties dated today."

# Contract with unusual formatting
UNUSUAL_FORMATTING_CONTRACT = """
    AGREEMENT




Section A - - - TERMS - - -

    1) The first term of this agreement states that...
    2) The second term includes provisions for...


***END OF AGREEMENT***
"""

# Contract with high-risk clauses for testing risk detection
HIGH_RISK_CONTRACT = """
SOFTWARE LICENSE AGREEMENT

1. LICENSE GRANT
Licensor grants Licensee a non-exclusive, non-transferable license to use
the Software solely for Licensee's internal business purposes.

2. INTELLECTUAL PROPERTY
All intellectual property rights in the Software remain with Licensor.
Licensee may not reverse engineer, decompile, or disassemble the Software.
Any improvements or modifications made by Licensee shall become the sole
property of Licensor.

3. WARRANTY DISCLAIMER
THE SOFTWARE IS PROVIDED "AS-IS" WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED. LICENSOR DISCLAIMS ALL WARRANTIES INCLUDING, WITHOUT LIMITATION,
WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE, AND
NON-INFRINGEMENT.

4. LIMITATION OF LIABILITY
IN NO EVENT SHALL LICENSOR BE LIABLE FOR ANY DAMAGES WHATSOEVER, INCLUDING
DIRECT, INDIRECT, INCIDENTAL, SPECIAL, CONSEQUENTIAL, OR PUNITIVE DAMAGES.
LICENSOR'S TOTAL LIABILITY SHALL NOT EXCEED ONE HUNDRED DOLLARS ($100).

5. INDEMNIFICATION
Licensee shall indemnify and hold harmless Licensor from any and all claims,
damages, losses, costs, and expenses (including reasonable attorneys' fees)
arising from Licensee's use of the Software, regardless of cause.

6. TERMINATION
Licensor may terminate this Agreement immediately and without notice for any
reason or no reason. Upon termination, Licensee must destroy all copies of
the Software and certify such destruction in writing.

7. GOVERNING LAW
This Agreement shall be governed by the laws of the State of Delaware,
without regard to its conflict of laws provisions.
"""

# Empty contract for edge case testing
EMPTY_CONTRACT = ""

# Whitespace-only contract for edge case testing
WHITESPACE_CONTRACT = "   \n\n\t\t\n   "
