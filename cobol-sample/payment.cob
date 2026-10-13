       IDENTIFICATION DIVISION.
       PROGRAM-ID. PAYMENT.
      * Subprogram called by ORDERPRG.
       DATA DIVISION.
       LINKAGE SECTION.
       01 LS-USER-ID        PIC 9(5).
       01 LS-PRODUCT-ID     PIC 9(5).
       01 LS-STATUS         PIC X(20).
       PROCEDURE DIVISION USING LS-USER-ID LS-PRODUCT-ID LS-STATUS.
       PAY-MAIN.
           PERFORM VALIDATE-INPUT
           IF LS-STATUS = SPACES
              MOVE "PAYMENT PROCESSED" TO LS-STATUS
           END-IF
           GOBACK.
       VALIDATE-INPUT.
           IF LS-USER-ID = 0
              MOVE "INVALID USER" TO LS-STATUS
           END-IF.
