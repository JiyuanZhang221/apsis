__author__ = 'Frederik Diehl'

from apsis.models.candidate import Candidate

class Experiment(object):
    """
    An Experiment is a set of parameter definitions and multiple candidate
    evaluations thereon.

    Attributes
    ----------
    name: string
        The name of the experiment. This does not have to be unique, but is
        for human orientation.
    parameter_definitions: dict of ParamDefs
        A dictionary of ParamDef instances. These define the parameter space
        over which optimization is possible.
    minimization_problem: bool
        Defines whether the experiment's goal is to find a minimum result - for
        example when evaluating errors - or a maximum result - for example when
        evaluating scores.

    candidates_pending: list of Candidate instances
        These Candidate instances have been generated by an optimizer to be
        evaluated at the next possible time, but are not yet assigned to a
        worker.
    candidates_working: list of Candidate instances
        These Candidate instances are currently being evaluated by workers.
    candidates_finished: list of Candidate instances
        These Candidate instances have finished evaluated.


    best_candidate: Candidate instance
        The as of yet best Candidate instance found, according to the result.
    """
    name = None

    parameter_definitions = None
    minimization_problem = None

    candidates_pending = None
    candidates_working = None
    candidates_finished = None

    best_candidate = None

    def __init__(self, name, parameter_definitions, minimization_problem=True):
        """
        Initializes an Experiment with a certain parameter definition.

        All of the Candidate lists are set to empty lists, representing an
        experiment with no work done.

        Parameters
        ----------
        name: string
            The name of the experiment. This does not have to be unique, but is
            for human orientation.

        parameter_definitions: dict of ParamDef
            Defines the parameter space of the experiment. Each entry of the
            dictionary has to be a ParamDef, and it is that space over which
            optimization will occur.
        minimization_problem: bool: True
            Defines whether the experiment's goal is to find a minimum result - for
            example when evaluating errors - or a maximum result - for example when
            evaluating scores. Is True by default.

        Raises
        ------
        ValueError:
            Iff parameter_definitions are not a dictionary.
        """
        self.name = name
        if not isinstance(parameter_definitions, dict):
            raise ValueError("parameter_definitions are not a dict.")
        self.parameter_definitions = parameter_definitions

        self.minimization_problem = minimization_problem

        self.candidates_finished = []
        self.candidates_pending = []
        self.candidates_working = []

    def add_finished(self, candidate):
        """
        Announces a Candidate instance to be finished evaluating.

        This moves the Candidate instance to the candidates_finished list and
        updates the best_candidate.

        Parameters
        ----------
        candidate: Candidate
            The Candidate to be added to the finished list.

        Raises
        ------
        ValueError:
            Iff candidate is not a Candidate object.
        """
        if not isinstance(candidate, Candidate):
            raise ValueError("candidate is not an instance of Candidate.")

        if candidate in self.candidates_pending:
            self.candidates_pending.remove(candidate)
        if candidate in self.candidates_working:
            self.candidates_working.remove(candidate)
        self.candidates_finished.append(candidate)
        if (self.best_candidate is None or
                    self.better_cand(candidate, self.best_candidate)):
            self.best_candidate = candidate

    def add_pending(self, candidate):
        """
        Adds a new pending Candidate object to be evaluated.

        This function should be used when a new pending candidate is supposed
        to be evaluated. If an old Candidate should be updated as just pausing,
        use the add_pausing function.
        Parameters
        ----------
        candidate: Candidate
            The Candidate instance that is supposed to be evaluated soon.

        Raises
        ------
        ValueError:
            Iff candidate is no Candidate object.
        """
        if not isinstance(candidate, Candidate):
            raise ValueError("candidate is not an instance of Candidate.")
        self.candidates_pending.append(candidate)

    def add_working(self, candidate):
        """
        Updates the experiment to now start working on candidate.

        This updates candidates_working list and the candidates_pending list
        if candidate is in the candidates_pending list.

        Parameters
        ----------
        candidate: Candidate
            The Candidate instance that is currently being worked on.

        Raises
        ------
        ValueError:
            Iff candidate is no Candidate object.
        """
        if not isinstance(candidate, Candidate):
            raise ValueError("candidate is not an instance of Candidate.")
        if candidate in self.candidates_pending:
            self.candidates_pending.remove(candidate)
        self.candidates_working.append(candidate)

    def add_pausing(self, candidate):
        """
        Updates the experiment that work on candidate has been paused.

        This updates candidates_pending list and the candidates_working list
        if it contains the candidate.

        Parameters
        ----------
        candidate: Candidate
            The Candidate instance that is currently paused.

        Raises
        ------
        ValueError:
            Iff candidate is no Candidate object.

        """
        if not isinstance(candidate, Candidate):
            raise ValueError("candidate is not an instance of Candidate.")
        if candidate in self.candidates_working:
            self.candidates_working.remove(candidate)
        self.candidates_pending.append(candidate)

    def better_cand(self, candidateA, candidateB):
        """
        Determines whether CandidateA is better than candidateB in the context
        of this experiment.
        This is done as follows:
        If candidateA's result is None, it is not better.
        If candidateB's result is None, it is better.
        If it is a minimization problem and the result is smaller than B's, it
        is better. Corresponding for being a maximization problem.


        Parameters
        ----------
        candidateA: Candidate
            The candidate which should be better.
        candidateB: Candidate
            The baseline candidate.

        Returns
        -------
        result: bool
            True iff A is better than B.

        Raises
        ------
        ValueError:
            If candidateA or candidateB are no Candidates.
        """
        if not isinstance(candidateA, Candidate) and candidateA is not None:
            raise ValueError("candidateA is %s, but no Candidate instance."
                             %str(candidateA))
        if not isinstance(candidateB, Candidate) and candidateB is not None:
            raise ValueError("candidateB is %s, but no Candidate instance."
                             %str(candidateB))

        if candidateA is None:
            return False
        if candidateB is None:
            return True

        aResult = candidateA.result
        bResult = candidateB.result

        if aResult is None:
            return False
        if bResult is None:
            return True
        if self.minimization_problem:
            if aResult < bResult:
                return True
            else:
                return False
        else:
            if aResult > bResult:
                return True
            else:
                return False



    def warp_pt_in(self, params):
        warped_in = {}
        for name, value in params.iteritems():
            warped_in[name] = self.parameter_definitions[name].warp_in(value)
        return warped_in

    def warp_pt_out(self, params):
        warped_out = {}
        for name, value in params.iteritems():
            warped_out[name] = self.parameter_definitions[name].warp_out(value)
        return warped_out